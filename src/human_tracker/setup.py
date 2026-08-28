from setuptools import find_packages, setup

package_name = 'human_tracker'

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
    maintainer='thuytran',
    maintainer_email='thuytran@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
		'tracker_camlap = human_tracker.tracker_camlap:main',
    		'tracker_astra = human_tracker.tracker_astra:main',
        ],
    },
)
