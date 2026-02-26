import logging
import os
import secrets
from typing import Iterable, List, Sequence

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
from flask import Flask, abort, render_template_string, request
from werkzeug.wrappers import Response

app = Flask(__name__)

logging.basicConfig(level=os.getenv("ROLLING_LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Default to us-east-1 (developer can override with AWS_REGION / AWS_DEFAULT_REGION)
REGION = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
API_KEY = os.getenv("ROLLING_API_KEY")

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

def _paginate(
    client,
    operation: str,
    result_keys: Sequence[str],
    *,
    pagination_kwargs: dict | None = None,
    operation_kwargs: dict | None = None,
) -> Iterable[dict]:
    paginator = client.get_paginator(operation)
    for page in paginator.paginate(**(operation_kwargs or {}), **(pagination_kwargs or {})):
        data = page
        for key in result_keys:
            data = data.get(key, [])
        if isinstance(data, list):
            yield from data
        else:
            logger.debug("Unexpected paginator data shape for %s -> %s", operation, result_keys)


def _collect_instances() -> List[dict]:
    items: List[dict] = []
    try:
        for reservation in _paginate(
            ec2_client,
            "describe_instances",
            result_keys=("Reservations",),
            operation_kwargs={
                "Filters": [{"Name": "instance-state-name", "Values": ["running"]}],
            },
        ):
            for instance in reservation.get("Instances", []):
                items.append(
                    {
                        "ID": instance.get("InstanceId", "N/A"),
                        "State": instance.get("State", {}).get("Name", "unknown"),
                        "Type": instance.get("InstanceType", "unknown"),
                        "Public IP": instance.get("PublicIpAddress", "N/A"),
                    }
                )
    except (BotoCoreError, ClientError) as exc:
        logger.exception("Failed to collect EC2 instances")
        raise exc
    return items


def _collect_vpcs() -> List[dict]:
    try:
        vpcs_resp = ec2_client.describe_vpcs()
    except (BotoCoreError, ClientError) as exc:
        logger.exception("Failed to collect VPCs")
        raise exc

    return [
        {"VPC ID": vpc.get("VpcId", "N/A"), "CIDR": vpc.get("CidrBlock", "N/A")}
        for vpc in vpcs_resp.get("Vpcs", [])
    ]


def _collect_load_balancers() -> List[dict]:
    items: List[dict] = []
    try:
        for load_balancer in _paginate(elb_client, "describe_load_balancers", result_keys=("LoadBalancers",)):
            items.append(
                {
                    "LB Name": load_balancer.get("LoadBalancerName", "N/A"),
                    "DNS Name": load_balancer.get("DNSName", "N/A"),
                }
            )
    except (BotoCoreError, ClientError) as exc:
        logger.exception("Failed to collect load balancers")
        raise exc
    return items


def _collect_amis() -> List[dict]:
    items: List[dict] = []
    try:
        for image in _paginate(
            ec2_client,
            "describe_images",
            result_keys=("Images",),
            operation_kwargs={"Owners": ["self"]},
        ):
            items.append({"AMI ID": image.get("ImageId", "N/A"), "Name": image.get("Name", "N/A")})
    except (BotoCoreError, ClientError) as exc:
        logger.exception("Failed to collect AMIs")
        raise exc
    return items


def _fetch_identity() -> tuple[str, str]:
    whoami = sts_client.get_caller_identity()
    return whoami.get("Account", "unknown"), whoami.get("Arn", "unknown")


@app.after_request
def add_security_headers(response: Response) -> Response:
    response.headers.setdefault("Content-Security-Policy", "default-src 'self'")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Permissions-Policy", "geolocation=()")
    return response


@app.before_request
def require_api_key() -> None:
    if not API_KEY:
        abort(503, description="ROLLING_API_KEY is not set.")
    provided = request.headers.get("X-API-Key", "")
    if not secrets.compare_digest(provided, API_KEY):
        abort(401, description="Unauthorized.")


@app.route("/")
def home():
    # Verify credentials first
    try:
        account, arn = _fetch_identity()
    except (NoCredentialsError, ClientError, BotoCoreError):
        # Show inline PowerShell instructions
        return SETUP_HTML, 200

    try:
        instances = _collect_instances()
        vpc_data = _collect_vpcs()
        lb_data = _collect_load_balancers()
        ami_data = _collect_amis()
    except (BotoCoreError, ClientError):
        abort(502, description="Failed to query AWS APIs. Please try again later.")

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
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5001")), debug=False)
