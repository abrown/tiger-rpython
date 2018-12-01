class BenchmarkMeasurement:
    def __init__(self, cmd, results):
        self.command = cmd
        self.measurements = results

    def get_command(self):
        return self.command

    def get_as_float(self, field):
        return float(self.measurements[field]['value'])

    def get_as_int(self, field):
        return int(self.measurements[field]['value'])

    def get_variance(self, field):
        return float(self.measurements[field]['variance'].replace('%', '')) / 100

    def assert_no_os_interference(self):
        assert self.get_as_int('cpu-migrations') == 0
        assert self.get_as_int('context-switches') == 0
