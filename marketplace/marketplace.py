import os

from flask import Flask
import grpc

from recommendations_pb2 import BookCategory, RecommendationRequest
from recommendations_pb2_grpc import RecommendationsStub

app = Flask(__name__)

recommendations_host = os.getenv("RECOMMENDATIONS_HOST", "localhost")
recommendations_channel = grpc.insecure_channel(f"{recommendations_host}:50051")
recommendations_client = RecommendationsStub(recommendations_channel)

@app.route('/')
def render_homepage():
    header = """
        <!doctype html>
        <html lang="en">
        <head>
            <title>Online Books For You</title>
        </head>
        <body>
            <h1>Mystery books you may like</h1>
            <ul>
    """
    recommendations_request = RecommendationRequest(user_id=1, category=BookCategory.MYSTERY, max_results=3)
    recommendations_response = recommendations_client.Recommend(recommendations_request)
    recommendations_html_parts = []
    for book in recommendations_response.recommendations:
        recommendations_html_parts.append(f"<li>{book.title}</li>")

    footer = """
            </ul>
        </body>
    """
    return header + "\n".join(recommendations_html_parts) + footer
