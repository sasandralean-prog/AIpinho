from aipinho.services.runtime.governed_task_step_runner import GovernedTaskStepRunner


class TaskRunExecutor:
    def __init__(self, runner=None):
        self.runner = runner or GovernedTaskStepRunner()

    def execute_step(self, run, step, context):
        return self.runner.run(run, step, context)

    def status(self):
        return {
            "status": "ok",
            "service": "task_run_executor",
            "mode": "governed",
            "runner": self.runner.status(),
        }
