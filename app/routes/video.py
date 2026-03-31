from flask import Blueprint, Response
from app.services.camera_service import CameraService

video_bp = Blueprint('video', __name__)

@video_bp.route('/video_feed/<site_name>')
def video_feed(site_name):
    return Response(CameraService.generate_frames(site_name, "access", "principal"),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@video_bp.route('/video_feed/transport/<site_name>/<position>')
def video_feed_transport(site_name, position):
    return Response(CameraService.generate_frames(site_name, "transport", position),
                    mimetype='multipart/x-mixed-replace; boundary=frame')
