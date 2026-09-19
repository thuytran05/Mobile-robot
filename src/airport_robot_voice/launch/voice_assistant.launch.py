import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch.conditions import IfCondition
from launch_ros.actions import Node

def generate_launch_description():
    pkg = get_package_share_directory('airport_robot_voice')
    cfg = os.path.join(pkg, 'config')

    intents = os.path.join(cfg, 'intents.json')
    places = os.path.join(cfg, 'places.json')

    mode = LaunchConfiguration('mode')            # mic | keyboard
    engine = LaunchConfiguration('tts_engine')    # piper | espeak | gtts
    model = LaunchConfiguration('vosk_model')
    use_nav = LaunchConfiguration('use_nav')

    return LaunchDescription([
        DeclareLaunchArgument('mode', default_value='mic'),
        DeclareLaunchArgument('tts_engine', default_value='piper'),
        DeclareLaunchArgument('vosk_model',
                              default_value='/opt/vosk/vosk-model-small-vn-0.4'),
        DeclareLaunchArgument('use_nav', default_value='true'),

        Node(package='airport_robot_voice', executable='stt_node', name='stt_node',
             output='screen',
             parameters=[{'mode': mode, 'model_path': model, 'wake_word': ''}]),

        Node(package='airport_robot_voice', executable='intent_node', name='intent_node',
             output='screen',
             parameters=[{'intents_file': intents, 'places_file': places}]),

        Node(package='airport_robot_voice', executable='tts_node', name='tts_node',
             output='screen',
             parameters=[{'engine': engine}]),

        Node(package='airport_robot_voice', executable='nav_command_node',
             name='nav_command_node', output='screen',
             parameters=[{'places_file': places}],
             condition=IfCondition(use_nav)),
    ])
