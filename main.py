from collections import defaultdict
from typing import Dict, List

import click
import networkx as nx
from matplotlib import pyplot as plt


"""
C1 - C2
     -
     C3 --- R1 ---- R2
     -              -
     C4 - C5 - R3 - R4
     -              -
     R5 --- R6 ---- R7
"""
AREA_POSITIONS = {
    "C1": (-1, 3),
    "C2": (0, 3),
    "C3": (0, 2),
    "C4": (0, 1),
    "C5": (0.66, 1),
    "R1": (1, 2),
    "R2": (2, 2),
    "R3": (1.33, 1),
    "R4": (2, 1),
    "R5": (0, 0),
    "R6": (1, 0),
    "R7": (2, 0),
}

STREETS_LIST = [
    dict(name="street1", areas={"C1", "C2"}, floodable=False),
    dict(name="street2", areas={"C2", "C3"}, floodable=False),
    dict(name="street3", areas={"C3", "R1"}, floodable=False),
    dict(name="street4", areas={"R1", "R2"}, floodable=False),
    dict(name="street5", areas={"C3", "C4"}, floodable=True),
    dict(name="street6", areas={"R2", "R4"}, floodable=False),
    dict(name="street7", areas={"C4", "C5"}, floodable=True),
    dict(name="street8", areas={"C5", "R3"}, floodable=False),
    dict(name="street9", areas={"R3", "R4"}, floodable=False),
    dict(name="street10", areas={"C4", "R5"}, floodable=True),
    dict(name="street11", areas={"R4", "R7"}, floodable=False),
    dict(name="street12", areas={"R5", "R6"}, floodable=False),
    dict(name="street13", areas={"R6", "R7"}, floodable=False),
]


def is_commercial(area_name):
    return area_name.startswith("C")


def generate_flow_dict(populated_area_name: str,
                       area_state: int,
                       weighting: Dict[str, int],
                       communication: bool,
                       flow_per_commercial_area: int,
                       flow_per_residential_area: int,
                       public_transport_factor: float,
                       flooded_street_avoidance: int):
    flow_graph = nx.DiGraph()
    total_demand = 0
    for area_name, weight in weighting.items():
        if area_name != populated_area_name:
            total_demand += weight

    for area_name, weight in weighting.items():
        if area_name != populated_area_name:
            flow_graph.add_node(area_name, demand=weight)
        else:
            flow_graph.add_node(area_name, demand=-total_demand)
    for street in STREETS_LIST:
        areas = list(street["areas"])
        weight = flooded_street_avoidance if communication and street["floodable"] else 1
        flow_graph.add_edge(areas[0], areas[1], weight=weight, capacity=1000, label=street["name"])
        flow_graph.add_edge(areas[1], areas[0], weight=weight, capacity=1000, label=street["name"])

    flow_cost, flow_dict = nx.network_simplex(flow_graph)

    normalized_flow_dict = defaultdict(dict)
    for area1, dest in flow_dict.items():
        for area2, flow in dest.items():
            factor = flow_per_commercial_area if is_commercial(populated_area_name) else flow_per_residential_area
            if area_state == 2:
                factor = factor * public_transport_factor
            normalized_flow_dict[area1][area2] = flow / total_demand * factor

    return normalized_flow_dict


def create_weighting(area_name, area_state, weight_commercial_unpopulated, weight_commercial_populated,
                     weight_residential_unpopulated, weight_residential_populated):
    if is_commercial(area_name):
        if area_state == 0:
            return weight_commercial_unpopulated
        else:
            return weight_commercial_populated
    else:
        if area_state == 0:
            return weight_residential_unpopulated
        else:
            return weight_residential_populated


def merge_flow_dicts(flow_dicts: List[Dict[str, Dict[str, float]]]):
    result = defaultdict(int)
    for flow_dict in flow_dicts:
        for area1, dest in flow_dict.items():
            for area2, flow in dest.items():
                result[frozenset({area1, area2})] += flow
    return result


def plot_result(graph, flooding):
    populated_nodes = [n for n, data in graph.nodes(data=True) if data["state"] == 1]
    publictransport_nodes = [n for n, data in graph.nodes(data=True) if data["state"] == 2]
    nx.draw_networkx_nodes(graph, pos=AREA_POSITIONS, node_color="grey")
    nx.draw_networkx_nodes(graph, pos=AREA_POSITIONS, nodelist=populated_nodes,
                           node_color="black")  # , with_labels=True
    nx.draw_networkx_nodes(graph, pos=AREA_POSITIONS, nodelist=publictransport_nodes,
                           node_color="green")  # , with_labels=True

    nx.draw_networkx_labels(graph, pos=AREA_POSITIONS, font_size=10, font_color="white", font_family="sans-serif")
    nx.draw_networkx_edges(graph, pos=AREA_POSITIONS)
    nx.draw_networkx_edge_labels(graph, pos=AREA_POSITIONS, edge_labels=nx.get_edge_attributes(graph, "flow"))

    if flooding == 1:
        plt.text(-1, 0, "Flooding")
    elif flooding == 2:
        plt.text(-1, 0, "Flooding + \nCommunication")
    plt.show()


@click.command()
@click.option('--areas', required=True, help="12 area states in the form 0,0,2,1,... where 0: unpopulated, 1: populated, 2: public transport. Order is top left to bottom right.")
@click.option('--flooding', required=True, type=int, help="0: no flooding, 1: flooding, 2: flooding+communication")
@click.option('--plot', is_flag=True, default=False, show_default=True, help="If true, shows the resulting matplotlib plot.")
@click.option('--flow_per_commercial_area', type=int, default=100, help="Flow added to the system by each populated commercial area")
@click.option('--flow_per_residential_area', type=int, default=200, help="Flow added to the system by each populated residential area")
@click.option('--public_transport_factor', type=float, default=0.5, help="The flow added by areas with public transport is multiplied by this factor.")
@click.option('--weight_commercial_unpopulated', type=int, default=2, help="Target weight for unpopulated commercial areas")
@click.option('--weight_commercial_populated', type=int, default=4, help="Target weight for populated commercial areas")
@click.option('--weight_residential_unpopulated', type=int, default=1, help="Target weight for unpopulated residential areas")
@click.option('--weight_residential_populated', type=int, default=2, help="Target weight for populated residential areas")
@click.option('--flooded_street_density', type=float, default=2, help="The density of flooded streets is multiplied by this factor.")
@click.option('--flooded_street_avoidance', type=int, default=3, help="1 is a normal street. The higher this factor, the more cars try to avoid flooded roads when communication is enabled.")
def main(areas: str, flooding: int, plot: bool, flow_per_commercial_area: int, flow_per_residential_area: int,
         public_transport_factor: float, weight_commercial_unpopulated: int, weight_commercial_populated: int,
         weight_residential_unpopulated: int, weight_residential_populated: int, flooded_street_density: float,
         flooded_street_avoidance: int):
    area_states = [int(s) for s in areas.split(",")]
    assert len(area_states) == 12, f"Requires 12 area states, provided only {(len(area_states))}"
    areas = {area_name: area_state for area_name, area_state in zip(AREA_POSITIONS.keys(), area_states)}

    weighting = {area_name: create_weighting(area_name, area_state, weight_commercial_unpopulated,
                                             weight_commercial_populated, weight_residential_unpopulated,
                                             weight_residential_populated) for area_name, area_state in areas.items()}
    flow_dicts = []
    for area_name, area_state in areas.items():
        if area_state == 0:
            continue
        flow_dicts.append(generate_flow_dict(area_name, area_state, weighting,
                                             communication=flooding == 2,
                                             flow_per_commercial_area=flow_per_commercial_area,
                                             flow_per_residential_area=flow_per_residential_area,
                                             public_transport_factor=public_transport_factor,
                                             flooded_street_avoidance=flooded_street_avoidance))
    flows = merge_flow_dicts(flow_dicts)
    if flooding >= 1:
        for street in STREETS_LIST:
            if street["floodable"]:
                flows[frozenset(street["areas"])] *= flooded_street_density

    graph = nx.Graph()
    for area_name, area_state in areas.items():
        graph.add_node(area_name, state=area_state)
    for areas, flow in flows.items():
        graph.add_edge(*areas, flow=round(flow))  # , label=street["name"]

    if plot:
        plot_result(graph, flooding)

    result_flows = {frozenset({src, dst}): data["flow"] for src, dst, data in graph.edges(data=True)}
    ordered_result = [result_flows[frozenset(street["areas"])] for street in STREETS_LIST]
    click.echo(ordered_result)


if __name__ == "__main__":
    main()

"""

state:
0
1
2
    normal
    flooded
    communication

areas: 0,1,2,3,4,3,2,3,4,3


result: 0-1000

"""
