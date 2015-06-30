from setuptools import setup, find_packages

setup(
    name='pulp_ostree_extensions_admin',
    version='1.0.0a2',
    packages=find_packages(),
    url='http://www.pulpproject.org',
    license='GPLv2+',
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    description='pulp-admin extensions for ostree image support',
    entry_points={
        'pulp.extensions.admin': [
            'repo_admin = pulp_ostree.extensions.admin.pulp_cli:initialize',
        ]
    }
)
