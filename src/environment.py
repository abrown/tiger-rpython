# By importing the specific type of Environment here we ensure that, as long as clients import this file, they will
# receive the correct environment implementation
from src.environments.environment_without_display import Environment
from src.environments.environment_interface import EnvironmentInterface

assert issubclass(Environment, EnvironmentInterface)
