import os
import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
from flask import Flask, render_template_string, abort

app = Flask(__name__)

# Default to us-east-2 (your region), allow override via env
REGION = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))

# Use the default AWS credential chain (env vars, ~/.aws/credentials, IAM role, etc.)
session = boto3.Session(region_name=REGION)
ec2_client = session.client("ec2")
elb_client = session.client("elbv2")
sts_client = session.client("sts")

SETUP_HTML = """
<html>
<head>
  <title>AWS Setup Needed</title>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; padding: 24px; line-height: 1.5; }
    code, pre { background: #f6f6f6; padding: 8px 10px; border-radius: 6px; display: block; }
    h1, h2 { margin-top: 24px; }
    .note { color: #555; }
  </style>
</head>
<body>
  <h1>Set AWS credentials</h1>
  <p class="note">No AWS credentials were detected. Set them in <strong>PowerShell</strong> and refresh this page.</p>

  <h2>1) Temporary (current PowerShell session)</h2>
  <pre><code>$env:AWS_ACCESS_KEY_ID="your_key_id"
$env:AWS_SECRET_ACCESS_KEY="your_secret_key"
$env:AWS_DEFAULT_REGION="us-east-2"</code></pre>

  <h2>2) Permanent (persists across sessions)</h2>
  <pre><code>[System.Environment]::SetEnvironmentVariable("AWS_ACCESS_KEY_ID", "your_key_id", "User")
[System.Environment]::SetEnvironmentVariable("AWS_SECRET_ACCESS_KEY", "your_secret_key", "User")
[System.Environment]::SetEnvironmentVariable("AWS_DEFAULT_REGION", "us-east-2", "User")</code></pre>
  <p class="note">Restart PowerShell after setting permanent variables.</p>

  <h2>3) Or use AWS config files</h2>
  <p>Create/modify:</p>
  <pre><code># %UserProfile%\.aws\credentials
[default]
aws_access_key_id = your_key_id
aws_secret_access_key = your_secret_key

# %UserProfile%\.aws\config
[default]
region = us-east-2</code></pre>

  <h2>4) Test in PowerShell</h2>
  <pre><code>echo $env:AWS_ACCESS_KEY_ID
echo $env:AWS_SECRET_ACCESS_KEY
echo $env:AWS_DEFAULT_REGION</code></pre>
</body>
</html>
"""

@app.route("/")
def home():
    # Verify credentials first
    try:
        whoami = sts_client.get_caller_identity()  # raises if no/invalid creds
        account = whoami.get("Account", "unknown")
        arn = whoami.get("Arn", "unknown")
    except (NoCredentialsError, ClientError, BotoCoreError):
        # Show inline PowerShell instructions
        return SETUP_HTML, 200

    try:
        # --- EC2 Instances (running only) ---
        instances = []
        resp = ec2_client.describe_instances(
            Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
        )
        reservations = resp.get("Reservations", [])
        while True:
            for r in reservations:
                for i in r.get("Instances", []):
                    instances.append({
                        "ID": i.get("InstanceId", "N/A"),
                        "State": i.get("State", {}).get("Name", "unknown"),
                        "Type": i.get("InstanceType", "unknown"),
                        "Public IP": i.get("PublicIpAddress", "N/A"),
                    })
            token = resp.get("NextToken")
            if not token:
                break
            resp = ec2_client.describe_instances(NextToken=token)
            reservations = resp.get("Reservations", [])

        # --- VPCs ---
        vpcs_resp = ec2_client.describe_vpcs()
        vpc_data = [{"VPC ID": v.get("VpcId", "N/A"), "CIDR": v.get("CidrBlock", "N/A")}
                    for v in vpcs_resp.get("Vpcs", [])]

        # --- Load Balancers (ALB/NLB via elbv2) ---
        lbs = []
        lb_resp = elb_client.describe_load_balancers()
        lbs.extend(lb_resp.get("LoadBalancers", []))
        marker = lb_resp.get("NextMarker")
        while marker:
            lb_resp = elb_client.describe_load_balancers(Marker=marker)
            lbs.extend(lb_resp.get("LoadBalancers", []))
            marker = lb_resp.get("NextMarker")
        lb_data = [{"LB Name": lb.get("LoadBalancerName", "N/A"),
                    "DNS Name": lb.get("DNSName", "N/A")} for lb in lbs]

        # --- AMIs you own ---
        amis_resp = ec2_client.describe_images(Owners=["self"])
        ami_data = [{"AMI ID": a.get("ImageId", "N/A"), "Name": a.get("Name", "N/A")}
                    for a in amis_resp.get("Images", [])]

    except (BotoCoreError, ClientError) as e:
        msg = getattr(e, "response", {}).get("Error", {}).get("Message", str(e))
        abort(500, description=f"AWS API error: {msg}")

    html = """
    <html>
    <head>
      <title>AWS Resources</title>
      <style>
        body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; padding: 24px; }
        h1 { margin-top: 28px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; }
        th { background: #f6f6f6; text-align: left; }
        tr:nth-child(even) { background: #fafafa; }
        .meta { color: #666; font-size: 12px; margin-bottom: 16px; }
        .id { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace; }
      </style>
    </head>
    <body>
      <h1>AWS Resources</h1>
      <div class="meta">Region: {{ region }} • Account: <span class="id">{{ account }}</span> • Caller: <span class="id">{{ arn }}</span></div>

      <h1>EC2 Instances</h1>
      <table>
        <tr><th>ID</th><th>State</th><th>Type</th><th>Public IP</th></tr>
        {% for i in instance_data %}
          <tr><td class="id">{{ i['ID'] }}</td><td>{{ i['State'] }}</td><td>{{ i['Type'] }}</td><td>{{ i['Public IP'] }}</td></tr>
        {% endfor %}
        {% if instance_data|length == 0 %}<tr><td colspan="4">No running instances.</td></tr>{% endif %}
      </table>

      <h1>VPCs</h1>
      <table>
        <tr><th>VPC ID</th><th>CIDR</th></tr>
        {% for v in vpc_data %}<tr><td class="id">{{ v['VPC ID'] }}</td><td>{{ v['CIDR'] }}</td></tr>{% endfor %}
        {% if vpc_data|length == 0 %}<tr><td colspan="2">No VPCs found.</td></tr>{% endif %}
      </table>

      <h1>Load Balancers</h1>
      <table>
        <tr><th>LB Name</th><th>DNS Name</th></tr>
        {% for lb in lb_data %}<tr><td>{{ lb['LB Name'] }}</td><td class="id">{{ lb['DNS Name'] }}</td></tr>{% endfor %}
        {% if lb_data|length == 0 %}<tr><td colspan="2">No load balancers found.</td></tr>{% endif %}
      </table>

      <h1>Available AMIs (Owned by Account)</h1>
      <table>
        <tr><th>AMI ID</th><th>Name</th></tr>
        {% for a in ami_data %}<tr><td class="id">{{ a['AMI ID'] }}</td><td>{{ a['Name'] }}</td></tr>{% endfor %}
        {% if ami_data|length == 0 %}<tr><td colspan="2">No AMIs found.</td></tr>{% endif %}
      </table>
    </body>
    </html>
    """
    return render_template_string(
        html,
        region=REGION,
        account=account,
        arn=arn,
        instance_data=instances,
        vpc_data=vpc_data,
        lb_data=lb_data,
        ami_data=ami_data,
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5001")),
            debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
