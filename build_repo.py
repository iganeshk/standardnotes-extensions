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
import json
import os
import shutil
from subprocess import run, PIPE
import yaml


def main(base_url):
    '''
    main function
    '''
    while base_url.endswith('/'):
        base_url = base_url[:-1]

    base_dir = os.path.dirname(os.path.abspath(__file__))
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

        # Build extension info
        repo_name = ext['github'].split('/')[-1]
        # https://example.com/sub-domain/my-extension/version/index.html
        extension_url = '/'.join([base_url, repo_name, ext['main']])
        # https://example.com/sub-domain/my-extension/index.json
        extension_info_url = '/'.join([base_url, repo_name, 'index.json'])
        extension = dict(
            identifier=ext['id'],
            name=ext['name'],
            content_type=ext['content_type'],
            area=ext.get('area', None),
            # supplying version not really a concern since it's checked for
            version=ext['version'],
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
        )

        # Strip empty values
        extension = {k: v for k, v in extension.items() if v}

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

        # Generate JSON file for each extension
        with open(os.path.join(public_dir, repo_name, 'index.json'),
                  'w') as ext_json:
            json.dump(extension, ext_json, indent=4)

        extensions.append(extension)
        print('Loaded extension: {} - {}'.format(ext['name'],
                                                 ext_latest_version))

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


if __name__ == '__main__':
    main(os.getenv('URL', 'https://domain.com/extensions'))
