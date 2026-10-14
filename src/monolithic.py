"""Ordinary whole-graph SCC decision baseline, not a boundary summary.

Same normalized input, goals, weak justice and finite-change quantifier. No
producer/checker helpers, mask-product expansion, or certificate validation.
"""
from model import Graph

def live(graph: Graph, finite_changes: bool = False) -> bool:
    pending=set(range(graph.n))-graph.goals
    prefix={state:[] for state in pending}
    for edge in graph.edges:
        if edge.src in pending and edge.dst in pending:
            prefix[edge.src].append(edge.dst)
    reachable=set(graph.initial)&pending
    stack=list(reachable)
    while stack:
        state=stack.pop()
        for target in prefix[state]:
            if target not in reachable:
                reachable.add(target)
                stack.append(target)
    # Marked edges may occur in the prefix even when the recurrent suffix must
    # be ordinary. Compute reachability before filtering suffix edges.
    edges=[edge for edge in graph.edges if edge.src in reachable and
           edge.dst in reachable and (not finite_changes or not edge.change)]
    adjacent={state:[] for state in reachable}
    reverse={state:[] for state in reachable}
    for edge in edges:
        adjacent[edge.src].append(edge.dst)
        reverse[edge.dst].append(edge.src)
    seen=set()
    order=[]
    for root in range(graph.n):
        if root not in reachable: continue
        if root in seen: continue
        seen.add(root)
        dfs=[(root,iter(adjacent[root]))]
        while dfs:
            state,children=dfs[-1]
            child=next(children,None)
            if child is None:
                order.append(state)
                dfs.pop()
            elif child not in seen:
                seen.add(child)
                dfs.append((child,iter(adjacent[child])))
    component={}
    sizes=[]
    for root in reversed(order):
        if root in component: continue
        identifier=len(sizes)
        size=0
        component[root]=identifier
        stack=[root]
        while stack:
            state=stack.pop()
            size+=1
            for child in reverse[state]:
                if child not in component:
                    component[child]=identifier
                    stack.append(child)
        sizes.append(size)
    colors=[0]*len(sizes)
    cyclic=[size>1 for size in sizes]
    for edge in edges:
        source=component[edge.src]
        if source==component[edge.dst]:
            colors[source]|=edge.color
            cyclic[source]|=edge.src==edge.dst
    return not any(cycle and color==graph.full for cycle,color in zip(cyclic,colors))
