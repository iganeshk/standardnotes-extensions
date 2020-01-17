#!/usr/bin/env/ python3
# coding=utf-8
'''
Parse extensions/*.yaml files & build a directory with following structure:
public/
    |-my-extension-1/
    |   |-1.0.0/          <- version (to avoid static file caching issues)
    |   |   |-index.json  <- extension info
    |   |   |-index.html  <- extension entrance (component)
    |   |   |-dist        <- extension resources
    |   |   |-...         <- other files
    |-index.json          <- repo info, contain all extensions' info
'''
# from subprocess import run, PIPE
from zipfile import ZipFile
import json
import os
import shutil
import requests
import yaml


def get_environment(base_dir):
    """
    Load .env file if present
    """
    temp_envvar = yaml.load("""
        domain: https://domain.com/extensions
        github:
          username:
          token:
    """, Loader=yaml.FullLoader)
    if os.path.isfile(os.path.join(base_dir, ".env")):
        with open(os.path.join(base_dir, ".env")) as temp_env_file:
            temp_envvar = yaml.load(temp_env_file, Loader=yaml.FullLoader)
        return temp_envvar

    # Environment file missing
    print("Please set your environment file (read env.sample)")
    print("You might be rate limited while parsing extensions from Github, if you continue!")
    input("Press any key to continue: ")
    return temp_envvar


def process_zipball(repo_dir, release_version):
    """
    Get release zipball and extract archive without the root directory
    """
    with ZipFile(os.path.join(repo_dir, release_version) + ".zip", 'r') as zipball:
        for member in zipball.namelist():
            # Parse files without root directory
            filename = '/'.join(member.split('/')[1:])
            # Ignore the parent folder
            if filename == '': continue
            # Ignore dot files
            if filename.startswith('.'): continue
            source = zipball.open(member)
            try:
                target = open(os.path.join(repo_dir, release_version, filename), "wb")
                with source, target:
                    target = open(os.path.join(repo_dir, release_version, filename), "wb")
                    shutil.copyfileobj(source, target)
            except FileNotFoundError:
                # Create the directory
                os.makedirs(os.path.dirname(os.path.join(repo_dir, release_version, filename)))
                continue
    # Delete the archive zip
    os.remove(os.path.join(repo_dir, release_version) + ".zip")


def parse_extensions(base_dir, base_url, ghub_session):
    """
    Build Standard Notes extensions repository using Github meta-data
    """
    extension_dir = os.path.join(base_dir, 'extensions')
    public_dir = os.path.join(base_dir, 'public')
    if not os.path.exists(os.path.join(public_dir)):
        os.makedirs(public_dir)
    os.chdir(public_dir)

    extensions = []

    # Read and parse all extension info
    for extfiles in os.listdir(extension_dir):
        if not extfiles.endswith('.yaml'):
            continue

        with open(os.path.join(extension_dir, extfiles)) as extyaml:
            ext = yaml.load(extyaml, Loader=yaml.FullLoader)

        # Get extension Github meta-data
        ext_git_info = json.loads(ghub_session.get('https://api.github.com/repos/{github}/releases/latest'.format(**ext)).text)

        repo_name = ext['github'].split('/')[-1]
        repo_dir = os.path.join(public_dir, repo_name)

        # Check if extension directory alredy exists
        if not os.path.exists(repo_dir):
            os.makedirs(repo_dir)
        # Check if extension with current release alredy exists
        if not os.path.exists(os.path.join(repo_dir, ext_git_info['tag_name'])):
            os.makedirs(os.path.join(repo_dir, ext_git_info['tag_name']))
            # Grab the release and then unpack it
            with requests.get(ext_git_info['zipball_url'], stream=True) as r:
                with open(os.path.join(repo_dir, ext_git_info['tag_name']) + ".zip", 'wb') as f:
                    shutil.copyfileobj(r.raw, f)
            # unpack the zipball
            process_zipball(repo_dir, ext_git_info['tag_name'])
            # Build extension info
            # https://example.com/sub-domain/my-extension/version/index.html
            extension_url = '/'.join([base_url, repo_name, ext_git_info['tag_name'], ext['main']])
            # https://example.com/sub-domain/my-extension/index.json
            extension_info_url = '/'.join([base_url, repo_name, 'index.json'])
            extension = dict(
                identifier=ext['id'],
                name=ext['name'],
                content_type=ext['content_type'],
                area=ext.get('area', None),
                version=ext_git_info['tag_name'],
                description=ext.get('description', None),
                marketing_url=ext.get('marketing_url', None),
                thumbnail_url=ext.get('thumbnail_url', None),
                valid_until='2030-05-16T18:35:33.000Z',
                url=extension_url,
                download_url='https://github.com/{github}/archive/{version}.zip'.
                format(**ext),
                latest_url=extension_info_url,
                flags=ext.get('flags', []),
                dock_icon=ext.get('dock_icon', {}),
                layerable=ext.get('layerable', None),
                statusBar=ext.get('statusBar', None),
            )

            # Strip empty values
            extension = {k: v for k, v in extension.items() if v}

            """ To-be deprecated Method
            # Get the latest repository and parse for latest version
            # TO-DO: Implement usage of Github API for efficiency

            run([
                'git', 'clone', 'https://github.com/{github}.git'.format(**ext),
                '--quiet', '{}_temp'.format(repo_name)
            ],
                check=True)
            ext_latest = (run([
                'git', '--git-dir=' +
                os.path.join(public_dir, '{}_temp'.format(repo_name), '.git'),
                'rev-list', '--tags', '--max-count=1'
            ],
                              stdout=PIPE,
                              check=True).stdout.decode('utf-8').replace("\n", ""))
            ext_latest_version = run([
                'git', '--git-dir',
                os.path.join(public_dir, '{}_temp'.format(repo_name), '.git'),
                'describe', '--tags', ext_latest
            ],
                                     stdout=PIPE,
                                     check=True).stdout.decode('utf-8').replace(
                                         "\n", "")

            # Tag the latest releases
            extension['version'] = ext_latest_version
            extension['url'] = '/'.join([
                base_url, repo_name, '{}'.format(ext_latest_version), ext['main']
            ])
            extension['download_url'] = (
                'https://github.com/{}/archive/{}.zip'.format(
                    ext['github'], ext_latest_version))

            # check if latest version already exists
            if not os.path.exists(
                    os.path.join(public_dir, repo_name,
                                 '{}'.format(ext_latest_version))):
                shutil.move(
                    os.path.join(public_dir, '{}_temp'.format(repo_name)),
                    os.path.join(public_dir, repo_name,
                                 '{}'.format(ext_latest_version)))
                # Delete .git resource from the directory
                shutil.rmtree(
                    os.path.join(public_dir, repo_name,
                                 '{}'.format(ext_latest_version), '.git'))
            else:
                # clean-up
                shutil.rmtree(os.path.join(public_dir,
                                           '{}_temp'.format(repo_name)))

            """
            # Generate JSON file for each extension
            with open(os.path.join(public_dir, repo_name, 'index.json'),
                      'w') as ext_json:
                json.dump(extension, ext_json, indent=4)

            extensions.append(extension)
            print('Loaded extension: {} - {}'.format(ext['name'],
                                                     ext_git_info['tag_name']))

    os.chdir('..')

    # Generate the index JSON file
    with open(os.path.join(public_dir, 'index.json'), 'w') as ext_json:
        json.dump(
            dict(
                content_type='SN|Repo',
                valid_until='2030-05-16T18:35:33.000Z',
                packages=extensions,
            ),
            ext_json,
            indent=4,
        )

    # Terminate Session
    ghub_session.close()


def main():
    """
    teh main function
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Get environment variables
    env_var = get_environment(base_dir)
    base_url = env_var['domain']
    while base_url.endswith('/'):
        base_url = base_url[:-1]

    # Get a re-usable session object using user credentials
    ghub_session = requests.Session()
    ghub_session.auth = (env_var['github']['username'], env_var['github']['token'])
    try:
        ghub_verify = ghub_session.get("https://api.github.com/")
        if not ghub_verify.headers['status'] == "200 OK":
            print("Error: %s " % ghub_verify.headers['status'])
            print("Bad Github credentials in the .env file, check and try again.")
            exit(1)
    except Exception as e:
        print("Error %s" % e)
    # Build extensions
    parse_extensions(base_dir, base_url, ghub_session)

if __name__ == '__main__':
    # If URL variable
    main()
