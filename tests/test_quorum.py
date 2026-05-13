from node_service.node_state import parse_peers


def test_parse_peers():
    peers = parse_peers("N1=http://node1:8001,N2=http://node2:8002")
    assert peers["N1"] == "http://node1:8001"
    assert peers["N2"] == "http://node2:8002"
