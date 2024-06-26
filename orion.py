"""
This is the cli file for orion, tool to detect regressions using hunter
"""

# pylint: disable = import-error, line-too-long
import logging
import sys
import warnings
import click
import uvicorn
from pkg.logrus import SingletonLogger
from pkg.runTest import run
from pkg.utils import load_config
from pkg.types import OptionMap
import pkg.constants as cnsts

warnings.filterwarnings("ignore", message="Unverified HTTPS request.*")
warnings.filterwarnings(
    "ignore", category=UserWarning, message=".*Connecting to.*verify_certs=False.*"
)


class MutuallyExclusiveOption(click.Option):
    """Class to implement mutual exclusivity between options in click

    Args:
        click (Option): _description_
    """

    def __init__(self, *args, **kwargs):
        self.mutually_exclusive = set(kwargs.pop("mutually_exclusive", []))
        help = kwargs.get("help", "")  # pylint: disable=redefined-builtin
        if self.mutually_exclusive:
            ex_str = ", ".join(self.mutually_exclusive)
            kwargs["help"] = help + (
                " NOTE: This argument is mutually exclusive with "
                " arguments: [" + ex_str + "]."
            )
        super().__init__(*args, **kwargs)

    def handle_parse_result(self, ctx, opts, args):
        if self.mutually_exclusive.intersection(opts) and self.name in opts:
            raise click.UsageError(
                f"Illegal usage: `{self.name}` is mutually exclusive with "
                f"arguments `{', '.join(self.mutually_exclusive)}`."
            )
        return super().handle_parse_result(ctx, opts, args)


def validate_anomaly_options(ctx, param, value): # pylint: disable = W0613
    """ validate options so that can only be used with certain flags
    """
    if value or (
        ctx.params.get("anomaly_window") or ctx.params.get("min_anomaly_percent")
    ):
        if not ctx.params.get("anomaly_detection"):
            raise click.UsageError(
                "`--anomaly-window` and `--min-anomaly-percent` can only be used when `--anomaly-detection` is enabled."
            )
    return value


@click.group()
def cli(max_content_width=120):  # pylint: disable=unused-argument
    """
    Orion is a tool which can run change point detection for set of runs using statistical models
    """


# pylint: disable=too-many-locals
@cli.command(name="cmd")
@click.option("--config", default="config.yaml", help="Path to the configuration file")
@click.option(
    "--output-path", default="output.csv", help="Path to save the output csv file"
)
@click.option("--debug", default=False, is_flag=True, help="log level")
@click.option(
    "--hunter-analyze",
    is_flag=True,
    help="run hunter analyze",
    cls=MutuallyExclusiveOption,
    mutually_exclusive=["anomaly_detection"],
)
@click.option("--anomaly-window", type=int, callback=validate_anomaly_options, help="set window size for moving average for anomaly-detection")
@click.option("--min-anomaly-percent", type=int, callback=validate_anomaly_options, help="set minimum percentage difference from moving average for data point to be detected as anomaly")
@click.option(
    "--anomaly-detection",
    is_flag=True,
    help="run anomaly detection algorithm powered by isolation forest",
    cls=MutuallyExclusiveOption,
    mutually_exclusive=["hunter_analyze"],
)
@click.option(
    "-o",
    "--output-format",
    type=click.Choice([cnsts.JSON, cnsts.TEXT]),
    default=cnsts.TEXT,
    help="Choose output format (json or text)",
)
@click.option("--uuid", default="", help="UUID to use as base for comparisons")
@click.option(
    "--baseline", default="", help="Baseline UUID(s) to to compare against uuid"
)
def cmd_analysis(**kwargs):
    """
    Orion runs on command line mode, and helps in detecting regressions
    """
    level = logging.DEBUG if kwargs["debug"] else logging.INFO
    logger_instance = SingletonLogger(debug=level).logger
    logger_instance.info("🏹 Starting Orion in command-line mode")
    kwargs["configMap"] = load_config(kwargs["config"])
    OptionMap.set_map(kwargs)
    output = run()
    if output is None:
        logger_instance.error("Terminating test")
        sys.exit(0)
    for test_name, result_table in output.items():
        print(test_name)
        print("=" * len(test_name))
        print(result_table)


@cli.command(name="daemon")
@click.option("--debug", default=False, is_flag=True, help="log level")
@click.option("--port", default=8080, help="set port")
def rundaemon(debug, port):
    """
    Orion runs on daemon mode
    \b
    """
    level = logging.DEBUG if debug else logging.INFO
    logger_instance = SingletonLogger(debug=level).logger
    logger_instance.info("🏹 Starting Orion in Daemon mode")
    uvicorn.run("pkg.daemon:app", port=port)


if __name__ == "__main__":
    if len(sys.argv) <= 1:
        cli.main(["--help"])
    else:
        cli.add_command(cmd_analysis)
        cli.add_command(rundaemon)
        cli()
