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
from subprocess import run, PIPE
import sys
import os
import json
import shutil
from zipfile import ZipFile
from socket import gethostname as getlocalhostname
import requests
import yaml

LOCAL_HOSTNAME = getlocalhostname()

def get_environment(base_dir):
    """
    Parse the environment variables from .env
    """
    temp_env_var = yaml.load("""
        github:
          username:
          token:
        public_dir: public
        extensions_dir: extensions
        domain: https://domain.com/extensions
        stdnotes_extensions_list: standardnotes-extensions-list.txt
    """, Loader=yaml.FullLoader)
    env_var = {}
    if os.path.isfile(os.path.join(base_dir, ".env")):
        with open(os.path.join(base_dir, ".env")) as temp_env_file:
            env_var = yaml.load(temp_env_file, Loader=yaml.FullLoader)

        # if user hasn't updated the env, copy defaults to yaml dictionary
    for key in temp_env_var:
        try:
            if not env_var[key]:
                env_var[key] = temp_env_var[key]
        except KeyError as e:
            env_var[key] = temp_env_var[key]

    return env_var


def process_zipball(repo_dir, release_version):
    """
    Grab the release zipball and extract it without the root/parent/top directory
    """
    with ZipFile(os.path.join(repo_dir, release_version) + ".zip",
                 'r') as zipball:
        for member in zipball.namelist():
            # Parse files list excluding the top/parent/root directory
            filename = '/'.join(member.split('/')[1:])
            # Now ignore it
            if filename == '': continue
            # Ignore dot files
            if filename.startswith('.'): continue
            source = zipball.open(member)
            try:
                target = open(
                    os.path.join(repo_dir, release_version, filename), "wb")
                with source, target:
                    target = open(
                        os.path.join(repo_dir, release_version, filename),
                        "wb")
                    shutil.copyfileobj(source, target)
            except (FileNotFoundError, IsADirectoryError):
                # Create the directory
                os.makedirs(
                    os.path.dirname(
                        os.path.join(repo_dir, release_version, filename)))
                continue
    # Delete the archive zip
    os.remove(os.path.join(repo_dir, release_version) + ".zip")


def git_clone_method(ext_yaml, public_path, ext_has_update):
    """
    Get the latest repository and parse for metadata
    """
    repo_name = ext_yaml['github'].split('/')[-1]
    repo_dir = os.path.join(public_path, repo_name)
    try:
        run([
            'git', 'clone', 'https://github.com/{github}.git'.format(**ext_yaml),
            '--quiet', '{}_tmp'.format(repo_name)
        ],
            check=True)
        ext_last_commit = (run([
            'git', '--git-dir=' +
            os.path.join(public_path, '{}_tmp'.format(repo_name), '.git'),
            'rev-list', '--tags', '--max-count=1'
        ],
                               stdout=PIPE,
                               check=True).stdout.decode('utf-8').replace(
                                   "\n", ""))
        ext_version = run([
            'git', '--git-dir',
            os.path.join(public_path, '{}_tmp'.format(repo_name), '.git'),
            'describe', '--tags', ext_last_commit
        ],
                          stdout=PIPE,
                          check=True).stdout.decode('utf-8').replace("\n", "")

        # check if the latest version already exist
        if not os.path.exists(os.path.join(repo_dir, ext_version)):
            ext_has_update = True
            shutil.move(
                os.path.join(public_path, '{}_tmp'.format(repo_name)),
                os.path.join(public_path, repo_name, '{}'.format(ext_version)))
            # Delete .git resource from the directory
            shutil.rmtree(
                os.path.join(public_path, repo_name, '{}'.format(ext_version),
                             '.git'))
        else:
            # ext already up-to-date
            # print('Extension: {} - {} (already up-to-date)'.format(ext_yaml['name'], ext_version))
            # clean-up
            shutil.rmtree(os.path.join(public_path, '{}_tmp'.format(repo_name)))
        return ext_version, ext_has_update
    except Exception as e:
        print('Skipping: {:38s}\t(github repository not found)'.format(repo_name))
        return '0.0', False


def parse_extensions(base_dir, extensions_dir, public_dir, base_url, stdnotes_ext_list_path, ghub_headers):
    """
    Build Standard Notes extensions repository using Github meta-data
    """
    extension_path = extensions_dir
    public_path = public_dir
    os.chdir(public_path)

    extensions = []
    std_ext_list = []
    std_ext_list = parse_stdnotes_extensions(stdnotes_ext_list_path)
    # Get all extensions, sort extensions alphabetically along by their by type
    extfiles = [x for x in sorted(os.listdir(extension_path)) if not x.endswith('theme.yaml') and x.endswith('.yaml')]
    themefiles = [y for y in sorted(os.listdir(extension_path)) if y.endswith('theme.yaml')]
    extfiles.extend(themefiles)

    for extfile in extfiles:
        with open(os.path.join(extension_path, extfile)) as extyaml:
            ext_yaml = yaml.load(extyaml, Loader=yaml.FullLoader)
        ext_has_update = False
        repo_name = ext_yaml['github'].split('/')[-1]
        repo_dir = os.path.join(public_path, repo_name)
        # If we have valid github personal access token
        if ghub_headers:
            # Get extension's github release meta-data
            ext_git_info = json.loads(
                requests.get(
                    'https://api.github.com/repos/{github}/releases/latest'.
                    format(**ext_yaml), headers=ghub_headers).text)
            try:
                ext_version = ext_git_info['tag_name']
            except KeyError:
                # No github releases found
                print('Skipping: {:38s}\t(github repository not found)'.format(
                    ext_yaml['name']))
                continue
            # Check if extension directory already exists
            if not os.path.exists(repo_dir):
                os.makedirs(repo_dir)
            # Check if extension with current release already exists
            if not os.path.exists(os.path.join(repo_dir, ext_version)):
                ext_has_update = True
                os.makedirs(os.path.join(repo_dir, ext_version))
                # Grab the release and then unpack it
                with requests.get(ext_git_info['zipball_url'], headers=ghub_headers,
                                  stream=True) as zipball_stream:
                    with open(
                            os.path.join(repo_dir, ext_version) + ".zip",
                            'wb') as zipball_file:
                        shutil.copyfileobj(zipball_stream.raw, zipball_file)
                # unpack the zipball
                process_zipball(repo_dir, ext_version)
        else:
            ext_version, ext_has_update = git_clone_method(
                ext_yaml, public_path, ext_has_update)

        if extfile in std_ext_list:
            ext_id = ext_yaml['id'].rsplit('.', 1)[1]
            ext_yaml['id'] = '%s.%s' % (LOCAL_HOSTNAME, ext_id)

        # Build extension info (stateless)
        # https://domain.com/sub-domain/my-extension/index.json
        extension = dict(
            identifier=ext_yaml['id'],
            name=ext_yaml['name'],
            content_type=ext_yaml['content_type'],
            area=ext_yaml.get('area', None),
            version=ext_version,
            description=ext_yaml.get('description', None),
            marketing_url=ext_yaml.get('marketing_url', None),
            thumbnail_url=ext_yaml.get('thumbnail_url', None),
            valid_until='2030-05-16T18:35:33.000Z',
            url='/'.join([base_url, repo_name, ext_version, ext_yaml['main']]),
            download_url='https://github.com/{}/archive/{}.zip'.format(
                ext_yaml['github'], ext_version),
            latest_url='/'.join([base_url, repo_name, 'index.json']),
            flags=ext_yaml.get('flags', []),
            dock_icon=ext_yaml.get('dock_icon', {}),
            layerable=ext_yaml.get('layerable', None),
            statusBar=ext_yaml.get('statusBar', None),
        )

        # Strip empty values
        extension = {k: v for k, v in extension.items() if v}

        # Check if extension is already up-to-date
        if ext_has_update:
            # Generate JSON file for each extension
            with open(os.path.join(public_path, repo_name, 'index.json'),
                      'w') as ext_json:
                json.dump(extension, ext_json, indent=4)
            if extfile.endswith("theme.yaml"):
                print('Theme: {:34s} {:6s}\t(updated)'.format(
                    ext_yaml['name'], ext_version.strip('v')))
            else:
                print('Extension: {:30s} {:6s}\t(updated)'.format(
                    ext_yaml['name'], ext_version.strip('v')))
        else:
            # ext already up-to-date
            if extfile.endswith("theme.yaml"):
                print('Theme: {:34s} {:6s}\t(already up-to-date)'.format(
                    ext_yaml['name'], ext_version.strip('v')))
            else:
                print('Extension: {:30s} {:6s}\t(already up-to-date)'.format(
                    ext_yaml['name'], ext_version.strip('v')))

        extensions.append(extension)
    os.chdir('..')

    # Generate the main repository index JSON
    # https://domain.com/sub-domain/my-index.json
    with open(os.path.join(public_path, 'index.json'), 'w') as ext_json:
        json.dump(
            dict(
                content_type='SN|Repo',
                valid_until='2030-05-16T18:35:33.000Z',
                packages=extensions,
            ),
            ext_json,
            indent=4,
        )
    print("\nProcessed: {:20s}{} extensions. (Components: {}, Themes: {})".format("", len(extfiles), len(extfiles)-len(themefiles), len(themefiles)))
    print("Repository Endpoint URL: {:6s}{}/index.json".format("", base_url))

def parse_stdnotes_extensions(stdnotes_ext_list_path):
    """
    To circumvent around the issue: https://github.com/standardnotes/desktop/issues/789
    We'll be parsing standard note's extensions package ids with local hostname followed
    by package name
    """
    if not os.path.exists(stdnotes_ext_list_path):
        print("\n⚠️ WARNING: Unable to locate standard notes extensions list file, make sure you've \
            cloned the source repository properly\
            ")
        print("You may encounter issues registering extensions, checkout ")
        print("https://github.com/standardnotes/desktop/issues/789 for more details\n")
    else:
        std_exts_list = []
        with open(stdnotes_ext_list_path) as list_file:
            for line in list_file:
                if not line.startswith('#'):
                    std_exts_list.append(line.rstrip())
        return std_exts_list


def main():
    """
    teh main function
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Get environment variables
    env_var = {}
    env_var = get_environment(base_dir)
    base_url = env_var["domain"]
    extensions_dir = env_var['extensions_dir']
    if os.path.exists(os.path.join(base_dir, extensions_dir)):
        extensions_dir = os.path.join(base_dir, extensions_dir)
    else:
        print("\n⚠️ WARNING: Unable to locate extensions directory, make sure you've \
            cloned the source repository properly and try again")
        sys.exit(1)
    public_dir = env_var['public_dir']
    if os.path.exists(os.path.join(base_dir, public_dir)):
        public_dir = os.path.join(base_dir, public_dir)
    else:
        os.makedirs(os.path.join(base_dir, public_dir))
        public_dir = os.path.join(base_dir, public_dir)

    stdnotes_ext_list = env_var['stdnotes_extensions_list']
    stdnotes_ext_list_path = os.path.join(base_dir, stdnotes_ext_list)
    ghub_auth_complete = False
    ghub_headers = False

    if env_var['github']['token']:
        # Get a re-usable session object using user credentials
        ghub_headers = {'Authorization': f'token %s' % env_var['github']['token']}
        try:
            ghub_verify = requests.get("https://api.github.com/", headers=ghub_headers)
            if not ghub_verify.status_code == 200:
                print("ERROR: %s " % ghub_verify.headers['status'])
                print(
                    "Bad Github credentials in the .env file, check and try again."
                )
                sys.exit(1)
            ghub_auth_complete = True
        except Exception as e:
            print("ERROR: %s" % e)

    if not ghub_auth_complete:
        # Environment file missing
        print(
            "Environment variables not set (have a look at env.sample). Using git-clone method instead"
        )
        input(
            "⚠️ WARNING: This is an in-efficient process\nPress any key to go ahead anyway: ")

    # Build extensions
    parse_extensions(base_dir, extensions_dir, public_dir, base_url, stdnotes_ext_list_path, ghub_headers)
    sys.exit(0)

if __name__ == '__main__':
    main()
