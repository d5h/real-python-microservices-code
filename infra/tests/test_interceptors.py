from concurrent import futures
from contextlib import contextmanager
from tempfile import gettempdir
from typing import Callable, Dict, List
from uuid import uuid4

import grpc
import pytest

from dummy_pb2 import DummyRequest, DummyResponse
import dummy_pb2_grpc

from infra.service_interceptor import Interceptor, MetricsLogger

SpecialCaseFunction = Callable[[str], str]

class DummyService(dummy_pb2_grpc.DummyServiceServicer):
    def __init__(self, special_cases: Dict[str, SpecialCaseFunction]):
        self._special_cases = special_cases

    def Execute(self, request: DummyRequest, context: grpc.ServicerContext) -> DummyResponse:
        inp = request.input
        if inp in self._special_cases:
            output = self._special_cases[inp](inp)
        else:
            output = inp
        return DummyResponse(output=output)

@contextmanager
def dummy_client(special_cases: Dict[str, SpecialCaseFunction], interceptors: List[Interceptor]):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=1), interceptors=interceptors)
    dummy_service = DummyService(special_cases)
    dummy_pb2_grpc.add_DummyServiceServicer_to_server(dummy_service, server)

    uds_path = f"{gettempdir()}/{uuid4()}.sock"
    server.add_insecure_port(f"unix://{uds_path}")
    server.start()

    channel = grpc.insecure_channel(f"unix://{uds_path}")
    client = dummy_pb2_grpc.DummyServiceStub(channel)

    try:
        yield client
    finally:
        server.stop(None)

def test_metrics_logger():
    metrics_logger = MetricsLogger()
    interceptors = [metrics_logger]

    special_cases = {
        "error": lambda r, c: 1 / 0
    }
    with dummy_client(special_cases=special_cases, interceptors=interceptors) as client:
        assert client.Execute(DummyRequest(input="foo")).output == "foo"
        assert len(metrics_logger.num_calls) == 1
        assert metrics_logger.num_calls["/DummyService/Execute"] == 1
        assert len(metrics_logger.num_errors) == 0

        with pytest.raises(grpc.RpcError):
            assert client.Execute(DummyRequest(input="error"))

        assert len(metrics_logger.num_calls) == 1
        assert metrics_logger.num_calls["/DummyService/Execute"] == 2
        assert len(metrics_logger.num_errors) == 1
        assert metrics_logger.num_errors["/DummyService/Execute"] == 1
