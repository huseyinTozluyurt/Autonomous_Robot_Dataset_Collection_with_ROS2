from setuptools import find_packages, setup

package_name = 'deliverybot_recording'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='huseyin',
    maintainer_email='huseyin@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'data_recorder_node = deliverybot_recording.data_recorder_node:main',
            'cmd_vel_ml_logger_node = deliverybot_recording.cmd_vel_ml_logger_node:main',
        ],
    },
)
