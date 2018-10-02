# By importing the specific type of Environment here we ensure that, as long as clients import this file, they will
# receive the correct environment implementation
from src.environment_with_paths import Environment
from src.environment_interface import EnvironmentInterface

assert issubclass(Environment, EnvironmentInterface)
