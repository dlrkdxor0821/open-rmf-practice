from setuptools import find_packages
from setuptools import setup

package_name = 'libi_rmf_tasks'

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
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='leekt',
    maintainer_email='dlrkdxor0821@gmail.com',
    description='libi RMF 배달 task dispatch + 팔 perform_action (M4).',
    license='Apache License 2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'dispatch_delivery=libi_rmf_tasks.dispatch_delivery:main',
        ],
    },
)
