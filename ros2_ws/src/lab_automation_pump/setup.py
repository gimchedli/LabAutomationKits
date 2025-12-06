from setuptools import setup, find_packages

package_name = 'lab_automation_pump'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/pump.launch.py']),
    ],
    install_requires=['setuptools', 'PyCmdMessenger', 'pyserial'],
    zip_safe=True,
    maintainer='Alejandro Lorite Mora',
    maintainer_email='lori@itu.dk',
    description='ROS 2 pump controller package wrapping microcontroller service and exposing action server and state publisher.',
    license='MIT',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'pump_node = lab_automation_pump.node:main',
            'pump_client = lab_automation_pump.client:main',
        ],
    },
)
