import pandas as pd
import csv
import json
import numpy as np
import mizani.formatters as mizani
import plotnine as p9
import tabulate as tab
from argparse import Namespace
import io
import os
import sys
from enum import Enum

import pyco_proc

def read_latest_result_file(bench, tool, timeout):
    assert tool != ""

    #substring to filter files with the same timeout
    timeout_str = f"to{timeout}-"
    matching_files = []
    for root, _, files in os.walk(bench):
        for file in files:
            if tool in file and timeout_str in file:
                matching_files.append(os.path.join(root, file))
    if not matching_files:
        print(f"WARNING: {tool} has no .tasks file for {bench}")
        return ""
    latest_file_name = sorted(matching_files, key = lambda x: x[-23:])[-1]
    with open(latest_file_name) as latest_file:
        return latest_file.read()


def drop_first_input(raw_data):
    """Removes the first input file from every row of a .tasks file.

    Equivalence benchmarks have two input files per row (original;compared circuit).
    pyco_proc expects one, so only the second (compared) circuit is kept as the name.
    """
    out = io.StringIO()
    writer = csv.writer(out, delimiter=';', quotechar='"', doublequote=False,
                        escapechar='\\', quoting=csv.QUOTE_MINIMAL, lineterminator='\n')
    reader = csv.reader(io.StringIO(raw_data), delimiter=';', quotechar='"',
                        doublequote=False, escapechar='\\')
    for row in reader:
        if len(row) >= 4:  # status;tool;input1;input2;...
            del row[2]
        writer.writerow(row)
    return out.getvalue()


def load_tasks(paths, drop_first=False):
    """Loads .tasks files directly, no folder or naming conventions needed.

    Args:
        paths (str or list): file paths and/or glob patterns, e.g. "../results/*/*.tasks"
        drop_first (bool): True for equivalence results (two input files per row)

    The benchmark is the file name up to "-to<timeout>-" (as named by run_*_bench.sh),
    the tool is read from the rows. If a benchmark has several files for the same tool,
    the newest (by name) is used.

    Returns:
        DataFrame in the same format as load_benches (one row per circuit/pair and benchmark).
    """
    import glob
    import re
    if isinstance(paths, str):
        paths = [paths]
    files = sorted({f for p in paths for f in (glob.glob(p) or [p])})

    # (benchmark, tool) -> newest file
    chosen = {}
    for f in files:
        name = os.path.basename(f)
        m = re.match(r"(.+?)-to\d+-", name)
        bench = m.group(1) if m else os.path.splitext(name)[0]
        with open(f) as fd:
            raw = fd.read()
        if drop_first:
            raw = drop_first_input(raw)
        tools = {row[1] for row in csv.reader(io.StringIO(raw), delimiter=';', quotechar='"',
                                              doublequote=False, escapechar='\\') if len(row) > 1}
        for tool in tools:
            if (bench, tool) not in chosen or name > os.path.basename(chosen[(bench, tool)][0]):
                chosen[(bench, tool)] = (f, raw)

    dfs = []
    for bench in sorted({b for b, _ in chosen}):
        input_data = "".join(raw if raw.endswith("\n") else raw + "\n"
                             for (b, _), (_, raw) in sorted(chosen.items()) if b == bench)
        buf = io.StringIO()
        old_stdout = sys.stdout
        try:
            sys.stdout = buf
            pyco_proc.proc_res(io.StringIO(input_data), Namespace(csv=True, html=False, text=False, tick=False))
        finally:
            sys.stdout = old_stdout
        df = pd.read_csv(io.StringIO(buf.getvalue()), sep=";", dtype='unicode')
        df["benchmark"] = bench
        dfs.append(df)

    df_all = pd.concat(dfs, ignore_index=True)
    for tool in sorted({t for _, t in chosen}):
        for metric in ["runtime", "memory"]:
            col = f"{tool}-{metric}"
            if col not in df_all.columns:
                df_all[col] = float('inf') if metric == "runtime" else 0
            df_all[col] = pd.to_numeric(df_all[col], errors='coerce').fillna(float('inf') if metric == "runtime" else 0).astype(float)
    print("loaded:", ", ".join(f"{b}/{t} <- {os.path.relpath(f)}" for (b, t), (f, _) in sorted(chosen.items())))
    return df_all


def load_benches(benches, tools, timeout=120, drop_first=False):
    """drop_first=True for equivalence benchmarks (two input files per row), see drop_first_input."""
    dfs = dict()
    for bench in benches:
        input_data = ""
        for tool in tools:
            assert tool != ""
            raw_data = read_latest_result_file(bench, tool, timeout)
            if drop_first:
                raw_data = drop_first_input(raw_data)

            # Skip lines that reference NL_ files
            filtered_lines = []
            for line in raw_data.splitlines():
                if "NL_" not in line:
                    filtered_lines.append(line)
            input_data += "\n".join(filtered_lines) + "\n"

        # Capture CSV output from pyco_proc.proc_res
        buf = io.StringIO()
        old_stdout = sys.stdout
        try:
            sys.stdout = buf
            pyco_proc.proc_res(io.StringIO(input_data), Namespace(csv=True, html=False, text=False, tick=False))
        finally:
            sys.stdout = old_stdout
        csv_output = buf.getvalue()

        # Read CSV into DataFrame
        df = pd.read_csv(io.StringIO(csv_output), sep=";", dtype='unicode')

        # Ensure each tool has runtime and memory columns
        for tool in tools:
            for metric in ["runtime", "memory"]:
                col = f"{tool}-{metric}"
                if col not in df.columns:
                    df[col] = float('inf') if metric == "runtime" else 0

        df["benchmark"] = bench
        dfs[bench] = df

    # Combine all benchmarks into a single DataFrame
    df_all = pd.concat(dfs.values(), ignore_index=True)

    # Convert runtime and memory columns to float
    for tool in tools:
        for metric in ["runtime", "memory"]:
            col = f"{tool}-{metric}"
            df_all[col] = pd.to_numeric(df_all[col], errors='coerce').fillna(float('inf') if metric == "runtime" else 0).astype(float)

    return df_all


def _prepare_scatter_data(df, x_tool, y_tool, col, xname=None, yname=None):
    """Prepare data for scatter plots by setting up column names and copying dataframe.
    
    Args:
        df: Input dataframe
        x_tool: Tool name for x-axis
        y_tool: Tool name for y-axis  
        col: Column type ("runtime" or "states")
        xname: Custom x-axis name (optional)
        yname: Custom y-axis name (optional)
        
    Returns:
        tuple: (prepared_df, x_col, y_col, xname, yname)
    """
    if xname is None:
        xname = x_tool
    if yname is None:
        yname = y_tool

    x_col = f"{x_tool}-{col}"
    y_col = f"{y_tool}-{col}"

    # work on a copy so we don't mutate the caller's dataframe
    df = df.copy(deep=True)

    # coerce plotting columns to numeric floats to avoid discrete/continuous scale errors
    df[x_col] = pd.to_numeric(df[x_col], errors='coerce').astype(float)
    df[y_col] = pd.to_numeric(df[y_col], errors='coerce').astype(float)

    return df, x_col, y_col, xname, yname

def _apply_scatter_points(scatter, x_col, y_col, color_column, color_by_benchmark, show_legend, point_size=1.0):
    """Apply scatter points and rug plots to a ggplot object.
    
    Args:
        scatter: ggplot object
        x_col: x-axis column name
        y_col: y-axis column name
        color_column: column to use for coloring
        color_by_benchmark: whether to color by benchmark
        show_legend: whether to show legend
        point_size: size of points
        
    Returns:
        ggplot object with points added
    """
    if color_by_benchmark:
        scatter += p9.aes(x=x_col, y=y_col, color=color_column)
        scatter += p9.geom_point(size=point_size, na_rm=True, show_legend=show_legend, raster=True)
        # rug plots
        scatter += p9.geom_rug(na_rm=True, sides="tr", alpha=0.05, raster=True)
    else:
        scatter += p9.aes(x=x_col, y=y_col, color=color_column)
        scatter += p9.geom_point(size=point_size, na_rm=True, show_legend=show_legend, raster=True, color="orange")
        # rug plots
        scatter += p9.geom_rug(na_rm=True, sides="tr", alpha=0.05, raster=True, color="orange")
    
    return scatter

def _apply_scatter_theme(scatter, width, height, transparent, show_legend, legend_width):
    """Apply common theme elements to scatter plot.
    
    Args:
        scatter: ggplot object
        width: figure width
        height: figure height  
        transparent: whether background should be transparent
        show_legend: whether to show legend
        legend_width: additional width for legend
        
    Returns:
        ggplot object with theme applied
    """
    if show_legend:
        width += legend_width
        
    scatter += p9.theme_bw()
    scatter += p9.theme(panel_grid_major=p9.element_line(color='#666666', alpha=0.5))
    scatter += p9.theme(panel_grid_minor=p9.element_blank())
    scatter += p9.theme(figure_size=(width, height))
    scatter += p9.theme(axis_text=p9.element_text(size=24, color="black"))
    scatter += p9.theme(axis_title=p9.element_text(size=24, color="black"))
    scatter += p9.theme(legend_text=p9.element_text(size=12))
    scatter += p9.theme(legend_key_width=2)
    
    
    if transparent:
        scatter += p9.theme(
            plot_background=p9.element_blank(),
            panel_background = p9.element_rect(alpha=0.0),
            panel_border = p9.element_rect(colour = "black"),
            legend_background=p9.element_rect(alpha=0.0),
            legend_box_background=p9.element_rect(alpha=0.0),
        )

    if not show_legend:
        scatter += p9.theme(legend_position='none')
        
    return scatter

def _add_scatter_reference_lines(scatter, clamp_domain, dash_pattern=(0, (6, 2))):
    """Add reference lines (diagonal, vertical, horizontal) to scatter plot.
    
    Args:
        scatter: ggplot object
        clamp_domain: domain limits [min, max]
        dash_pattern: line dash pattern
        
    Returns:
        ggplot object with reference lines added
    """
    scatter += p9.geom_abline(intercept=0, slope=1, linetype=dash_pattern)  # diagonal
    scatter += p9.geom_vline(xintercept=clamp_domain[1], linetype=dash_pattern)  # vertical rule
    scatter += p9.geom_hline(yintercept=clamp_domain[1], linetype=dash_pattern)  # horizontal rule
    return scatter

def scatter_plot(df, x_tool, y_tool, property="runtime", title=None, timeout=120, clamp=True, clamp_domain=[0.01, 120], xname=None, yname=None, log=True, width=6, height=6, show_legend=True, legend_width=2, file_name_to_save=None, transparent=False, color_by_benchmark=True, color_column="benchmark"):
    """Returns scatter plot for property comparison between two tools.

    Args:
        df (Dataframe): Dataframe containing the values to plot
        x_tool (str): name of the tool for x-axis
        y_tool (str): name of the tool for y-axis
        property (str): name of the property to plot. Defaults to "runtime".
        timeout (int, optional): timeout value. Defaults to 120.
        clamp (bool, optional): Whether values outside of clamp_domain are cut off. Defaults to True.
        clamp_domain (list, optional): The min/max values to plot. Defaults to [0.01, 120].
        xname (str, optional): Name of the x axis. Defaults to None, uses x_tool.
        yname (str, optional): Name of the y axis. Defaults to None, uses y_tool.
        log (bool, optional): Use logarithmic scale. Defaults to True.
        width (int, optional): Figure width in inches. Defaults to 6.
        height (int, optional): Figure height in inches. Defaults to 6.
        show_legend (bool, optional): Print legend. Defaults to True.
        legend_width (int, optional): Additional width for legend. Defaults to 2.
        file_name_to_save (str, optional): If not None, save the result to file_name_to_save.pdf. Defaults to None.
        transparent (bool, optional): Whether the generated plot should have transparent background. Defaults to False.
        color_by_benchmark (bool, optional): Whether the dots should be colored based on the benchmark. Defaults to True.
        color_column (str, optional): Name of the column to use for coloring. Defaults to 'benchmark'.
    """
    assert len(clamp_domain) == 2

    POINT_SIZE = 1.0
    DASH_PATTERN = (0, (6, 2))

    # Prepare data
    df, x_col, y_col, xname, yname = _prepare_scatter_data(df, x_tool, y_tool, property, xname, yname)

    # formatter for axes' labels
    ax_formatter = mizani.custom_format('{:n}')

    if clamp:  # clamp overflowing values if required
        clamp_domain[1] = timeout
        df.loc[df[x_col] > clamp_domain[1], x_col] = clamp_domain[1]
        df.loc[df[y_col] > clamp_domain[1], y_col] = clamp_domain[1]
        # values below the axis (e.g. 0.0 s, which log10 cannot show) go on the lower edge
        df.loc[df[x_col] < clamp_domain[0], x_col] = clamp_domain[0]
        df.loc[df[y_col] < clamp_domain[0], y_col] = clamp_domain[0]

    # generate scatter plot
    scatter = p9.ggplot(df)
    scatter = _apply_scatter_points(scatter, x_col, y_col, color_column, color_by_benchmark, show_legend, POINT_SIZE)
    scatter += p9.labs(x=xname, y=yname, title=title)

    if log:  # log scale
        scatter += p9.scale_x_log10(limits=clamp_domain, labels=ax_formatter)
        scatter += p9.scale_y_log10(limits=clamp_domain, labels=ax_formatter)
    else:
        scatter += p9.scale_x_continuous(limits=clamp_domain, labels=ax_formatter)
        scatter += p9.scale_y_continuous(limits=clamp_domain, labels=ax_formatter)

    scatter = _apply_scatter_theme(scatter, width, height, transparent, show_legend, legend_width)
    scatter = _add_scatter_reference_lines(scatter, clamp_domain, DASH_PATTERN)

    if file_name_to_save != None:
        scatter.save(filename=f"{file_name_to_save}.pdf", dpi=500, verbose=False)

    return scatter

def scatter_two_files(file_x, file_y, property="runtime", timeout=300, drop_first=True, file_name_to_save=None, **kwargs):
    """Scatter plot of two .tasks files (one tool each, same benchmark), colored by circuit type.

    The circuit type is the folder the circuit is in (e.g. RevLib, Feynman, qaoa).
    Runtime is the tool's wall time measured by the wrapper (###runtime).
    Runs without a correct eq/neq answer (timeout, error, unknown, wrong answer) are drawn
    on the timeout edge; the expected answer is eq for *-opt benchmarks, neq otherwise.

    Args:
        file_x (str): .tasks file of the tool on the x-axis
        file_y (str): .tasks file of the tool on the y-axis
        property (str): "runtime" or "memory"
        timeout (int): timeout of the runs (-s), used as the edge of the plot
        drop_first (bool): True for equivalence results (two input files per row)
        file_name_to_save (str, optional): save to file_name_to_save.pdf
        kwargs: passed to scatter_plot (e.g. title, xname, yname, clamp_domain)
    """
    df = load_tasks([file_x, file_y], drop_first=drop_first)

    # tool of each file (first file's tool on the x-axis)
    def tool_of(f):
        with open(f) as fd:
            return next(csv.reader(fd, delimiter=';', quotechar='"', doublequote=False, escapechar='\\'))[1]
    x_tool, y_tool = tool_of(file_x), tool_of(file_y)
    if x_tool == y_tool:
        raise ValueError(f"both files are from the same tool ({x_tool})")
    for t in (x_tool, y_tool):
        # a tool with only failed runs (e.g. unsupported gates) has no result/runtime columns
        if f"{t}-result" not in df.columns:
            df[f"{t}-result"] = "ERR"
        if f"{t}-runtime.1" not in df.columns:
            df[f"{t}-runtime.1"] = float("inf")

    df["type"] = df["name"].apply(lambda p: os.path.basename(os.path.dirname(str(p))))
    # expected answer from the benchmark name: *-opt pairs are equivalent, all others are not
    expected = df["benchmark"].str.endswith("-opt").map({True: "eq", False: "neq"})
    for t in (x_tool, y_tool):
        if property == "runtime":
            # wall time of the tool itself, measured by the wrapper (###runtime);
            # pycobench's own column is user CPU time incl. wrapper overhead (conversions, python start)
            df[f"{t}-runtime"] = pd.to_numeric(df[f"{t}-runtime.1"], errors="coerce")
        result = df[f"{t}-result"]
        unsolved = ~result.isin(["eq", "neq"])
        wrong = ~unsolved & (result != expected)
        if wrong.any():
            print(f"{t}: {wrong.sum()} wrong answer(s), drawn as unsolved")
        df.loc[unsolved | wrong, f"{t}-{property}"] = float("inf")

    if property == "runtime":
        kwargs.setdefault("clamp_domain", [0.01, timeout])
    else:
        timeout = kwargs.pop("max_value", 1e8)
        kwargs.setdefault("clamp_domain", [1e3, timeout])
    return scatter_plot(df, x_tool, y_tool, property=property, timeout=timeout,
                        color_column="type", file_name_to_save=file_name_to_save, **kwargs)


def cactus_plot(df, tools, timeout = 120, tool_names = None, start = 0, end = None, logarithmic_y_axis=True, width=6, height=6, show_legend=True, put_legend_outside=False, file_name_to_save=None, num_of_x_ticks=5):
    """Returns cactus plot (sorted runtimes of each tool in tools). To print the result use result.figure.savefig("name_of_file.pdf", transparent=True).

    Args:
        df (Dataframe): Dataframe containing for each tool in tools column tool-result and tool-runtime containing the result and runtime for each benchmark.
        tools (list): List of tools to plot.
        tool_names (dict, optional): Maps each tool to its name that is used in the legend. If not set (=None), the names are taken directly from tools.
        start (int, optional): The starting position of the x-axis. Defaults to 0.
        end (int, optional): The ending position of the x-axis. If not set (=None), defaults to number of benchmarks, i.e. len(df).
        logarithmic_y_axis (bool, optional): Use logarithmic scale for the y-axis. Defaults to True.
        width (int, optional): Figure width in inches. Defaults to 6.
        height (int, optional): Figure height in inches. Defaults to 6.
        show_legend (bool, optional): Print legend. Defaults to True.
        put_legend_outside (bool, optional): Whether to put legend outside the plot. Defaults to False.
        file_name_to_save (str, optional): If not None, save the result to file_name_to_save.pdf. Defaults to None.
        num_of_x_ticks (int, optional): Number of ticks on the x-axis. Defaults to 5.
    """
    if tool_names == None:
        tool_names = { tool:tool for tool in tools }

    if end == None:
        end = len(df)

    concat = dict()

    for tool in tools:
        name = tool_names[tool]

        concat[name] = pd.Series(sorted(get_solved(df, tool)[tool + "-runtime"].tolist()))

    concat = pd.DataFrame(concat)


    plt = concat.plot.line(figsize=(width, height))
    ticks = np.linspace(start, end, num_of_x_ticks, dtype=int)
    plt.set_xticks(ticks)
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.set_xlim([start, end])
    plt.set_ylim([0.1, timeout])
    if logarithmic_y_axis:
        plt.set_yscale('log')
    plt.set_xlabel("Instances", fontsize=16)
    plt.set_ylabel("Runtime [s]", fontsize=16)

    if show_legend:
        if put_legend_outside:
            plt.legend(bbox_to_anchor=(1.04, 1), loc='upper left',framealpha=0.1)
        else:
            plt.legend(loc='upper left',framealpha=0.1)

        # plt.axvline(x=end)

        # plt.get_legend().remove()
        # figlegend = pylab.figure(figsize=(4,4))
        # figlegend.legend(plt.get_children(), concat.columns, loc='center', frameon=False)
        # figlegend.savefig(f"graphs/fig-cactus-{file_name}-legend.pdf", dpi=1000, bbox_inches='tight')
        # plt.figure.savefig(f"graphs/fig-cactus-{file_name}.pdf", dpi=1000, bbox_inches='tight')

    plt.figure.tight_layout()
    if file_name_to_save != None:
        plt.figure.savefig(f"{file_name_to_save}.pdf", transparent=True)
    return plt

def sanity_check(df, tool, compare_with):
    """Returns dataframe containing rows of df, where df[tool-result] is different (sat vs. unsat) than the result of any of the tools in compare_with

    Args:
        compare_with (list): List of tools to compare with.
    """
    all_bad = []
    for tool_other in compare_with:
        pt = df
        pt = pt[((pt[tool+"-result"].str.strip() == 'sat') & (pt[tool_other+"-result"].str.strip() == 'unsat') | (pt[tool+"-result"].str.strip() == 'unsat') & (pt[tool_other+"-result"].str.strip() == 'sat'))]
        all_bad.append(pt)
    return pd.concat(all_bad).drop_duplicates()

def get_timeouts(df, tool):
    """Returns dataframe containing rows of df, where df[tool-result] is timeout, i.e., 'TO'"""
    print(df.columns.tolist())

def get_errors(df, tool):
    """Returns dataframe containing rows of df, where df[tool-result] is error, i.e., 'ERR'"""
    return df[(df[tool+"-states"].str.strip().isin(['ERR', 'MISSING']))]

def simple_table(df, tools, benches, separately=False, stat_from_valid=True):
    """
    Prints a simple table with statistics for each tool (runtime and memory).

    Args:
        df (DataFrame): Data
        tools (list): List of tools
        benches (list): List of benchmark sets
        separately (bool, optional): Should we print table for each benchmark separately. Defaults to False
        stat_from_valid (bool, optional): Should we compute stats from non-timeout runs only. Defaults to True
    """
    result = ""

    def print_table_from_full_df(df):
        header = ["tool", "✅", "❌", "time-total", "time-avg", "time-med", "memory-total", "memory-avg", "memory-med", "TO", "ERR"]
        table = [header]
        result_text = f"# of circuits: {len(df)}\n"
        result_text += "-"*100 + "\n"

        for tool in tools:
            runtime_col = df[f"{tool}-runtime"]
            memory_col = df[f"{tool}-memory"]

            # Compute valid rows (exclude TO/ERR)
            if stat_from_valid:
                valid_mask = runtime_col != float('inf')  # or any placeholder for timeout
                valid_df = df[valid_mask]
                runtime_col = valid_df[f"{tool}-runtime"]
                memory_col = valid_df[f"{tool}-memory"]

            # Count TO and ERR
            to = (df[f"{tool}-runtime"] == float('inf')).sum()
            err = (df[f"{tool}-runtime"].isna()).sum()

            table.append([
                tool,
                len(runtime_col),            # valid
                to + err,                    # invalid
                runtime_col.sum(),           # total runtime
                runtime_col.mean(),          # avg runtime
                runtime_col.median(),        # median runtime
                memory_col.sum(),            # total memory
                memory_col.mean(),           # avg memory
                memory_col.median(),         # median memory
                to,
                err
            ])

        result_text += tab.tabulate(table, headers='firstrow', floatfmt=".2f") + "\n"
        result_text += "-"*100 + "\n\n"
        return result_text

    if separately:
        for bench in benches:
            result += f"Benchmark {bench}\n"
            result += print_table_from_full_df(df[df["benchmark"] == bench])
    else:
        result += print_table_from_full_df(df[df["benchmark"].isin(benches)])

    return result

def add_vbs(df, tools_list, name = None):
    """Adds virtual best solvers from tools in tool_list

    Args:
        df (Dataframe): data
        tools_list (list): list of tools
        name (str, optional): Name of the vbs used for the new columns. If not set (=None), the name is generated from the name of tools in tool_list.

    Returns:
        Dataframe: same as df but with new columns for the vbs
    """
    if name == None:
        name = "+".join(tools_list)
    df[f"{name}-runtime"] = df[[f"{tool}-runtime" for tool in tools_list]].min(axis=1)
    def get_result(row):
        nonlocal tools_list
        if "sat" in [str(row[f"{tool}-result"]).strip() for tool in tools_list]:
            return "sat"
        elif "unsat" in [str(row[f"{tool}-result"]).strip() for tool in tools_list]:
            return "unsat"
        else:
            return "unknown"
    df[f"{name}-result"] = df.apply(get_result, axis=1) # https://stackoverflow.com/questions/26886653/create-new-column-based-on-values-from-other-columns-apply-a-function-of-multi
    return df

def write_latex_table_body(df, float_format="{:.2f}", format_index_name=True, index_to_latex=None):
    def format_index_name_default(name):
        if index_to_latex and name in index_to_latex:
            return index_to_latex[name]

        return name

    df_table = df
    if format_index_name:
        df_table = df.rename(index=format_index_name_default)
    return df_table.to_latex(buf=None, columns=None, header=False, index=True, na_rep='NaN', formatters=None, float_format=float_format.format, sparsify=None, index_names=True, bold_rows=False, column_format=None, longtable=None, escape=None, encoding=None, decimal='.', multicolumn=None, multicolumn_format=None, multirow=None, caption=None, label=None, position=None).splitlines()

def parse_classification(benchmark_name):
    """Parse classification CSV file for a specific benchmark and return pandas DataFrame.
    
    Args:
        benchmark_name (str): Name of the benchmark (will look for classifications/<benchmark>-classification.csv)
        
    Returns:
        pd.DataFrame: DataFrame with columns 'circuit', 'benchmark', and 'info' where info contains
                     a dictionary of classification properties
    """
    classification_csv_path = f"classifications/{benchmark_name}-classification.csv"
    
    # Read the classification CSV
    df_class = pd.read_csv(classification_csv_path, sep=';')
    
    # Get property columns (all columns except 'name')
    property_columns = [col for col in df_class.columns if col != 'name']
    
    # Create info column by combining all property columns into a dictionary
    def create_info_dict(row):
        info = {}
        for prop in property_columns:
            info[prop] = int(row[prop])
        return info
    
    # Create the result DataFrame
    result_df = pd.DataFrame({
        'circuit': df_class['name'],
        'benchmark': benchmark_name,
        'info': df_class.apply(create_info_dict, axis=1)
    })
    
    return result_df

def join_with_classification(main_df, classification_df, circuit_column='name', benchmark_column='benchmark'):
    """Join main dataframe with classification dataframe on automaton name and benchmark.
    
    Args:
        main_df (pd.DataFrame): Main dataframe containing benchmark results
        classification_df (pd.DataFrame): Classification dataframe from parse_classification()
        circuit_column (str, optional): Column name in main_df containing circuit names. 
                                         Defaults to 'name'.
        benchmark_column (str, optional): Column name in main_df containing benchmark names.
                                         Defaults to 'benchmark'.
        
    Returns:
        pd.DataFrame: Merged dataframe with classification info added
    """
    # Perform left join to preserve all rows from main_df
    result_df = main_df.merge(
        classification_df, 
        left_on=[circuit_column, benchmark_column], 
        right_on=['circuit', 'benchmark'], 
        how='left'
    )
    
    # Drop the redundant columns from classification_df
    if 'circuit' in result_df.columns:
        result_df = result_df.drop('circuit', axis=1)
    
    return result_df

def parse_classifications_for_benchmarks(benchmark_names):
    """Parse classification CSV files for multiple benchmarks and return combined DataFrame.
    
    Args:
        benchmark_names (list): List of benchmark names
        
    Returns:
        pd.DataFrame: Combined DataFrame with columns 'circuit', 'benchmark', and 'info'
    """
    classification_dfs = []
    
    for benchmark_name in benchmark_names:
        try:
            df = parse_classification(benchmark_name)
            classification_dfs.append(df)
        except FileNotFoundError:
            print(f"WARNING: Classification file not found for benchmark '{benchmark_name}'")
            continue
        except Exception as e:
            print(f"WARNING: Error parsing classification for benchmark '{benchmark_name}': {e}")
            continue
    
    if not classification_dfs:
        print("WARNING: No classification files could be loaded")
        return pd.DataFrame(columns=['circuit', 'benchmark', 'info'])
    
    # Combine all classification dataframes
    combined_df = pd.concat(classification_dfs, ignore_index=True)
    
    return combined_df

def plot_tool_vs_qubits(df, tools, benchmark, property="runtime", width=8, height=6, log_y=True,
                        show_legend=True, file_name_to_save=None, transparent=False,
                        timeout=120):
    """
    Plot runtime or memory vs number of qubits for multiple tools for a single benchmark.

    Args:
        df (pd.DataFrame): DataFrame containing 'num_qubits', benchmark column, tool runtime/memory columns.
        tools (list[str]): List of tool column prefixes (e.g., ['medusa-sylvan-base', 'medusa-motobuddy-base']).
        benchmark (str): Name of the benchmark to plot.
        property (str): "runtime" or "memory".
        width (int): Figure width in inches.
        height (int): Figure height in inches.
        log_y (bool): Use log scale for y-axis.
        show_legend (bool): Whether to display legend.
        file_name_to_save (str): If given, save figure to this PDF file.
        transparent (bool): Transparent background.
    
    Returns:
        ggplot object
    """

    # Filter for the given benchmark
    df_bench = df[df["benchmark"] == benchmark].copy()
    if df_bench.empty:
        raise ValueError(f"No data found for benchmark '{benchmark}'")

    # Melt the DataFrame to long format for ggplot
    plot_df = pd.melt(df_bench,
                      id_vars=["num_qubits"],
                      value_vars=[f"{tool}-{property}" for tool in tools],
                      var_name="tool",
                      value_name=property)

    # Clean tool names (remove "-runtime" or "-memory")
    plot_df["tool"] = plot_df["tool"].str.replace(f"-{property}", "", regex=False)

    # Convert runtime/memory to numeric
    plot_df[property] = pd.to_numeric(plot_df[property], errors="coerce")
    property_name=property.capitalize()

    # do not plot 0kB -> error
    if property=="memory":
        plot_df = plot_df[(plot_df[property] != 0) & (plot_df[property].notna())]
        property_name+=" (kB)"
    # do not plot timeout
    if property=="runtime":
        plot_df = plot_df[(plot_df[property] != float('inf'))]
        property_name+=" (s)"

    
    # ggplot line plot
    p = (
        p9.ggplot(plot_df, p9.aes(x="num_qubits", y=property, color="tool"))
        + p9.geom_line(size=1.5)
        + p9.geom_point(size=2)
        + p9.labs(x="Number of Qubits", y=property_name, title=f"{benchmark} ({property})")
        + p9.theme_bw()
        + p9.theme(
            figure_size=(width, height),
            axis_text=p9.element_text(size=14),
            axis_title=p9.element_text(size=16),
            legend_text=p9.element_text(size=12),
            legend_title=p9.element_text(size=14),
        )
    )

    if log_y:
        p += p9.scale_y_log10()

    if not show_legend:
        p += p9.theme(legend_position="none")

    if transparent:
        p += p9.theme(
            plot_background=p9.element_blank(),
            panel_background=p9.element_rect(alpha=0.0),
            legend_background=p9.element_rect(alpha=0.0),
        )

    if file_name_to_save is not None:
        p.save(filename=file_name_to_save, dpi=500, verbose=False)

    return p
