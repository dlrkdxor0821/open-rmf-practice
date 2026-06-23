from glob import glob
import os

from setuptools import find_packages
from setuptools import setup

package_name = 'libi_rmf_fleet_adapter'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(),
    data_files=[
        (
            'share/ament_index/resource_index/packages',
            ['resource/' + package_name],
        ),
        ('share/' + package_name, ['package.xml']),
        (
            os.path.join('share', package_name, 'config'),
            glob('config/*.yaml'),
        ),
        (
            os.path.join('share', package_name, 'launch'),
            glob('launch/*.launch.xml'),
        ),
    ],
    install_requires=['setuptools', 'fastapi>=0.79.0', 'uvicorn>=0.18.2'],
    zip_safe=True,
    maintainer='leekt',
    maintainer_email='dlrkdxor0821@gmail.com',
    description='libi RMF fleet adapter — EasyFullControl Python port of '
    'rmf_demos_fleet_adapter (slotcar backend for M2~M4 study).',
    license='Apache License 2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'fleet_adapter=libi_rmf_fleet_adapter.fleet_adapter:main',
            'fleet_manager=libi_rmf_fleet_adapter.fleet_manager:main',
            'manage_lane=libi_rmf_fleet_adapter.manage_lane:main',
        ],
    },
)
