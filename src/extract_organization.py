import boto3
import logging
import json


OU_filename = "logs/ou_list.json"

logger = logging.getLogger(__name__)
logging.basicConfig(filename=OU_filename, level=logging.INFO)

cli_profile_name = "XXXXXX"
role_orga = "XXXXXX"
root_ou_id = "XXXXXXX"

jump_account = boto3.session.Session(profile_name=cli_profile_name)


def get_ou_children(client, ou_id):
    """
    get the list of OU children for a given OU id
    args:
      client: boto3 organization client
      ou_id:  ID of the current OU
    returns:
      children:  OU
    """
    children = []
    paginator = client.get_paginator('list_organizational_units_for_parent')
    for page in paginator.paginate(ParentId=ou_id):
        for organization in page.get('OrganizationalUnits', []):
            accounts = []
            paginator_accounts = client.get_paginator('list_accounts_for_parent')
            for page_account in paginator_accounts.paginate(ParentId=organization['Id']):
                for account in page_account.get('Accounts', []):
                    accounts.append(dict(id=account['Id'], name=account['Name']))

            children.append(dict(id=organization['Id'], name=organization['Name'], accounts=accounts,
                                 child=get_ou_children(client, organization['Id']),
                                 scp=get_ou_scp(client, organization['Id'])))

    return children


def get_ou_scp(client, ou_id):

    response = client.list_policies_for_target(
        TargetId=ou_id,
        Filter='SERVICE_CONTROL_POLICY',
    )

    result = []
    if response.get('Policies'):
        for scp in response.get('Policies'):
            result.append(dict(Id=scp['Id'], Name=scp['Name']))

    return result


if __name__ == '__main__':
    sts = jump_account.client('sts')

    assumed_creds = sts.assume_role(RoleArn=role_orga,
                                    RoleSessionName='ExtractOrganization')

    client = boto3.client('organizations',
                          aws_access_key_id=assumed_creds['Credentials']['AccessKeyId'],
                          aws_secret_access_key=assumed_creds['Credentials']['SecretAccessKey'],
                          aws_session_token=assumed_creds['Credentials']['SessionToken'])
    accounts_root = []
    paginator_accounts_root = client.get_paginator('list_accounts_for_parent')
    for page_account_root in paginator_accounts_root.paginate(ParentId=root_ou_id):
        for account_root in page_account_root.get('Accounts', []):
            accounts_root.append(dict(id=account_root['Id'], name=account_root['Name']))

    result = dict(id=root_ou_id, name='Root account',
                  accounts=accounts_root, child=get_ou_children(client, root_ou_id),
                  scp=get_ou_scp(client, root_ou_id))

    with open(OU_filename, 'w+') as outputfile:
        json.dump(result, outputfile, indent=4)
