from setuptools import setup
import os
from glob import glob

package_name = 'airport_robot_voice'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.json')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='you',
    maintainer_email='you@example.com',
    description='Voice assistant cho mobile robot san bay',
    license='MIT',
    entry_points={
        'console_scripts': [
            'stt_node = airport_robot_voice.stt_node:main',
            'intent_node = airport_robot_voice.intent_node:main',
            'tts_node = airport_robot_voice.tts_node:main',
            'nav_command_node = airport_robot_voice.nav_command_node:main',
        ],
    },
)
