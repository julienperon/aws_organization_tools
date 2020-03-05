import boto3
import logging
import json


log_filename = "logs/extract_scp.log"

logger = logging.getLogger(__name__)
logging.basicConfig(filename=log_filename, level=logging.INFO)

cli_profile_name = "XXXXXXXX"
role_orga = "XXXXXXX"
root_ou_id = "XXXXXX"

jump_account = boto3.session.Session(profile_name=cli_profile_name)


def save_scp(client, scp_id):
    response = client.describe_policy(PolicyId=scp_id)
    with open(f"scp/{response['Policy']['PolicySummary']['Name']}.json", 'w+') as outputfile:
        json.dump(json.loads(response['Policy']['Content']), outputfile, indent=4)


if __name__ == '__main__':
    sts = jump_account.client('sts')

    assumed_creds = sts.assume_role(RoleArn=role_orga,
                                    RoleSessionName='ExtractSCP')

    client = boto3.client('organizations',
                          aws_access_key_id=assumed_creds['Credentials']['AccessKeyId'],
                          aws_secret_access_key=assumed_creds['Credentials']['SecretAccessKey'],
                          aws_session_token=assumed_creds['Credentials']['SessionToken'])
    policies=[]
    paginator_scp = client.get_paginator('list_policies')
    for page_scp in paginator_scp.paginate(Filter='SERVICE_CONTROL_POLICY'):
        for scp in page_scp.get('Policies', []):
            policies.append(scp['Id'])

    for policy_id in policies:
        save_scp(client, policy_id)
