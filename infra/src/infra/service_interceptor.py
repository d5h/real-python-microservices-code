import grpc

class Interceptor(grpc.ServerInterceptor):

    def intercept(self, next_handler, request, context, method_name):
        pass

    # Implementation of grpc.ServerInterceptor, do not override.
    def intercept_service(self, continuation, handler_call_details):
        return continuation(handler_call_details)
