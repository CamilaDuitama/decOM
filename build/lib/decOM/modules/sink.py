#!/usr/bin/env python3

from .utils import *
from os import path
import plotly.express as px


def create_vector(output_path, path_to_sources, key, accession, t):
    output = output_path + accession + "_vector/"
    if path.exists(output):
        subprocess.call(["rm", "-rf", output])
    subprocess.call(
        ["kmtricks", "filter", "--in-matrix", path_to_sources, "--key", key, "--output", output, "--out-types", "k,v"])
    subprocess.call(
        ["kmtricks", "aggregate", "-t", str(t), "--run-dir", output, "--count", accession + ":kmer", "--output",
         output + "counts/partition_100/" + accession + "_missing.txt"])
    return


def plot_results(sink, p_sinks, result, classes, output):
    if sink is not None:
        fig = px.histogram(result, x="Sink", y=["p_" + c for c in classes],
                           color_discrete_sequence=["#FF9900","#109618","#3366CC","#DC3912","#990099"], opacity=0.9,
                           title="Proportions for sinks estimated by decOM", barmode="stack")
        fig.update_layout(width=400, height=800, yaxis_title="Percentage (%)")
        fig.write_image(output + "result_plot_sinks.pdf", width=400, height=800, scale=5, engine="kaleido")
        fig.write_html(output + "result_plot_sinks.html")

    elif p_sinks is not None:
        fig = px.histogram(result.sort_values("p_aOral"), x="Sink", y=["p_" + c for c in classes],
                           color_discrete_sequence=["#FF9900","#109618","#3366CC","#DC3912","#990099"], opacity=0.9,
                           title="Proportions for sinks estimated by decOM", barmode="stack")
        fig.update_layout(width=800, height=500,yaxis_title="Percentage (%)")
        fig.write_image(output + "result_plot_sinks.pdf", width=1000, height=500, scale=5, engine="kaleido")
        fig.write_html(output + "result_plot_sinks.html")
    return
