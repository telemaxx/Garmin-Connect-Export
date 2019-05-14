"""
utility functions used in the garmin connect export

"""


def addARGS(PARSER, ACTIVITIES_DIRECTORY):
    global ARGS
    # TODO: Implement verbose and/or quiet options.
    PARSER.add_argument("--verbose", help="increase output verbosity", action="store_true")
    PARSER.add_argument("--version", help="print version and exit", action="store_true")
    PARSER.add_argument(
        "--username",
        help="your Garmin Connect username (otherwise, you will be prompted)",
        nargs="?",
    )
    PARSER.add_argument(
        "--password",
        help="your Garmin Connect password (otherwise, you will be prompted)",
        nargs="?",
    )
    PARSER.add_argument(
        "-c",
        "--count",
        nargs="?",
        default="1",
        help="number of recent activities to download, or 'all' (default: 1)",
    )
    PARSER.add_argument(
        "-e",
        "--external",
        nargs="?",
        default="",
        help="path to external program to pass CSV file too (default: )",
    )
    PARSER.add_argument(
        "-a",
        "--args",
        nargs="?",
        default="",
        help="additional arguments to pass to external program (default: )",
    )
    PARSER.add_argument(
        "-f",
        "--format",
        nargs="?",
        choices=["gpx", "tcx", "original"],
        default="gpx",
        help="export format; can be 'gpx', 'tcx', or 'original' (default: 'gpx')",
    )
    PARSER.add_argument(
        "-d",
        "--directory",
        nargs="?",
        default=ACTIVITIES_DIRECTORY,
        help="the directory to export to (default: './YYYY-MM-DD_garmin_connect_export')",
    )
    PARSER.add_argument(
        "-u",
        "--unzip",
        help="if downloading ZIP files (format: 'original'), unzip the file and removes the ZIP file",
        action="store_true",
    )
    PARSER.add_argument(
        "-j",
        "--json",
        help="keep or delete json and csv files if not needed (y = keep, n = delete)",
        choices=["y", "n"],
        default="y",

    )
