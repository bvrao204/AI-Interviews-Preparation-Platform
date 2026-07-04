"""
utils/eye_tracker.py
--------------------
Provides real-time browser-based Eye Contact Detection using MediaPipe Face Mesh.
Runs a background local HTTP server to receive updates from the browser iframe,
bypassing Streamlit's iframe sandboxing restrictions.
"""

import http.server
import socketserver
import threading
import urllib.parse
import uuid
import streamlit as st

# Global store to hold eye contact tracking stats for all active sessions
# Key: session_id
# Value: {"status": str, "counts": {"Looking at screen": int, "Looking away": int, "Reading from paper": int}}
EYE_CONTACT_DATA = {}

class EyeContactHTTPHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/update":
            query = urllib.parse.parse_qs(parsed.query)
            session_id = query.get("session_id", [""])[0]
            status = query.get("status", [""])[0]
            
            if session_id and status:
                if session_id not in EYE_CONTACT_DATA:
                    EYE_CONTACT_DATA[session_id] = {
                        "status": "Looking at screen",
                        "counts": {
                            "Looking at screen": 0,
                            "Looking away": 0,
                            "Reading from paper": 0
                        }
                    }
                
                # Update current status
                EYE_CONTACT_DATA[session_id]["status"] = status
                
                # Increment status count
                if status in EYE_CONTACT_DATA[session_id]["counts"]:
                    EYE_CONTACT_DATA[session_id]["counts"][status] += 1
            
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b"OK")
            
        elif parsed.path == "/reset":
            query = urllib.parse.parse_qs(parsed.query)
            session_id = query.get("session_id", [""])[0]
            if session_id in EYE_CONTACT_DATA:
                EYE_CONTACT_DATA[session_id] = {
                    "status": "Looking at screen",
                    "counts": {
                        "Looking at screen": 0,
                        "Looking away": 0,
                        "Reading from paper": 0
                    }
                }
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress request logging to keep the console clean
        return

def start_eye_tracker_server():
    """Starts the local TCP server on port 8503 to receive browser eye gaze updates."""
    def _run():
        try:
            # Re-usable port configuration
            socketserver.TCPServer.allow_reuse_address = True
            with socketserver.TCPServer(("127.0.0.1", 8503), EyeContactHTTPHandler) as httpd:
                httpd.serve_forever()
        except Exception:
            pass # Port already bound or running
            
    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

def get_session_id() -> str:
    """Gets or initializes a unique session ID for the user's browser session."""
    if "eye_tracker_session_id" not in st.session_state:
        st.session_state.eye_tracker_session_id = str(uuid.uuid4())
    return st.session_state.eye_tracker_session_id

def get_current_eye_status(session_id: str) -> str:
    """Returns the current state for the given session (e.g. 'Looking at screen')."""
    return EYE_CONTACT_DATA.get(session_id, {}).get("status", "Looking at screen")

def get_eye_contact_percentages(session_id: str) -> dict:
    """Returns percentages of time spent in each eye contact state."""
    data = EYE_CONTACT_DATA.get(session_id, {})
    counts = data.get("counts", {
        "Looking at screen": 0,
        "Looking away": 0,
        "Reading from paper": 0
    })
    total = sum(counts.values())
    if total == 0:
        return {
            "looking_at_screen": 100,
            "looking_away": 0,
            "reading_paper": 0
        }
    return {
        "looking_at_screen": round(counts.get("Looking at screen", 0) / total * 100),
        "looking_away": round(counts.get("Looking away", 0) / total * 100),
        "reading_paper": round(counts.get("Reading from paper", 0) / total * 100)
    }

def get_eye_tracker_html(session_id: str) -> str:
    """Generates the HTML string containing client-side MediaPipe eye tracking.
    Supports both desktop and mobile browsers (front-facing camera).
    """
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <style>
            body {{
                margin: 0;
                padding: 0;
                background: #0B0F19;
                color: #FFFFFF;
                font-family: 'Inter', sans-serif;
                overflow: hidden;
            }}
            #container {{
                position: relative;
                width: 100%;
                height: 100%;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
            }}
            video {{
                width: 100%;
                height: auto;
                max-height: 200px;
                border-radius: 12px;
                transform: scaleX(-1); /* Mirror camera feed */
                background: #111827;
                border: 1px solid rgba(255,255,255,0.08);
                object-fit: cover;
            }}
            canvas {{
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                transform: scaleX(-1); /* Mirror canvas landmarks */
                pointer-events: none;
            }}
            #overlay {{
                position: absolute;
                bottom: 10px;
                left: 10px;
                right: 10px;
                background: rgba(17, 24, 39, 0.85);
                border: 1px solid rgba(255,255,255,0.12);
                backdrop-filter: blur(8px);
                border-radius: 8px;
                padding: 8px 12px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                box-shadow: 0 4px 12px rgba(0,0,0,0.5);
            }}
            .status-badge {{
                padding: 4px 10px;
                border-radius: 12px;
                font-size: 0.75rem;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }}
            .status-looking-screen {{ background: rgba(16, 185, 129, 0.2); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.4); }}
            .status-looking-away   {{ background: rgba(245, 158, 11, 0.2);  color: #FBBF24; border: 1px solid rgba(245, 158, 11, 0.4); }}
            .status-reading-paper  {{ background: rgba(239, 68, 68, 0.2);   color: #F87171; border: 1px solid rgba(239, 68, 68, 0.4); }}
            .status-loading        {{ background: rgba(156, 163, 175, 0.2); color: #D1D5DB; border: 1px solid rgba(156, 163, 175, 0.4); }}
            #error-msg {{
                display: none;
                text-align: center;
                padding: 20px;
                color: #FBBF24;
                font-size: 0.85rem;
            }}

            /* Mobile responsive */
            @media (max-width: 768px) {{
                video {{
                    max-height: 180px;
                }}
                .status-badge {{
                    font-size: 0.65rem;
                    padding: 3px 8px;
                }}
                #overlay {{
                    padding: 6px 8px;
                }}
            }}
        </style>
        
        <!-- MediaPipe and Camera Utils CDNs -->
        <script src="https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js" crossorigin="anonymous"></script>
        <script src="https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/face_mesh.js" crossorigin="anonymous"></script>
    </head>
    <body>
        <div id="container">
            <video id="webcam" autoplay playsinline muted></video>
            <canvas id="output_canvas"></canvas>
            <div id="overlay">
                <span style="font-size: 0.8rem; font-weight: 600; color: #9CA3AF;">Eye Tracker</span>
                <span id="status_badge" class="status-badge status-loading">Initialising...</span>
            </div>
            <div id="error-msg">
                📷 Camera access is required for eye tracking.<br>
                Please allow camera permissions in your browser settings and reload.
            </div>
        </div>

        <script>
            const videoElement = document.getElementById('webcam');
            const canvasElement = document.getElementById('output_canvas');
            const canvasCtx = canvasElement.getContext('2d');
            const statusBadge = document.getElementById('status_badge');
            const errorMsg = document.getElementById('error-msg');
            
            const sessionId = "{session_id}";
            let lastStatus = "";

            function updatePythonState(status) {{
                if (status === lastStatus) return;
                lastStatus = status;
                
                // Update badge class
                statusBadge.className = 'status-badge';
                if (status === 'Looking at screen') {{
                    statusBadge.classList.add('status-looking-screen');
                }} else if (status === 'Looking away') {{
                    statusBadge.classList.add('status-looking-away');
                }} else if (status === 'Reading from paper') {{
                    statusBadge.classList.add('status-reading-paper');
                }} else {{
                    statusBadge.classList.add('status-loading');
                }}
                statusBadge.innerText = status;

                // Send live GET request back to background Python HTTP server
                fetch(`http://127.0.0.1:8503/update?session_id=${{sessionId}}&status=${{encodeURIComponent(status)}}`)
                    .catch(e => console.error("Error updating Python state:", e));
            }}

            function onResults(results) {{
                // Fit canvas sizing to active video stream
                if (canvasElement.width !== videoElement.videoWidth) {{
                    canvasElement.width = videoElement.videoWidth;
                    canvasElement.height = videoElement.videoHeight;
                }}

                canvasCtx.clearRect(0, 0, canvasElement.width, canvasElement.height);

                if (!results.multiFaceLandmarks || results.multiFaceLandmarks.length === 0) {{
                    updatePythonState("Looking away");
                    return;
                }}

                const landmarks = results.multiFaceLandmarks[0];

                // Draw Eye Contours and Iris connections
                canvasCtx.fillStyle = 'rgba(99, 102, 241, 0.4)';
                
                // Left & Right eye iris drawing
                const drawIris = (irisIndices) => {{
                    canvasCtx.beginPath();
                    irisIndices.forEach((idx, i) => {{
                        const pt = landmarks[idx];
                        const x = pt.x * canvasElement.width;
                        const y = pt.y * canvasElement.height;
                        if (i === 0) canvasCtx.moveTo(x, y);
                        else canvasCtx.lineTo(x, y);
                    }});
                    canvasCtx.closePath();
                    canvasCtx.fillStyle = '#34D399';
                    canvasCtx.fill();
                }};

                // MediaPipe face mesh refineLandmarks index values for irises
                if (landmarks.length > 468) {{
                    drawIris([468, 469, 470, 471, 472]); // Left Iris
                    drawIris([473, 474, 475, 476, 477]); // Right Iris
                }}

                // Bounding Box checks for Eye-Gaze & Head Yaw / Pitch
                const leftCheek = landmarks[234];
                const rightCheek = landmarks[454];
                const noseTip = landmarks[4];
                const forehead = landmarks[10];
                const chin = landmarks[152];

                // Head Yaw (Left / Right turn)
                const cheekDist = rightCheek.x - leftCheek.x;
                const noseRelativeX = (noseTip.x - leftCheek.x) / cheekDist;

                // Head Pitch (Up / Down tilt)
                const faceHeight = chin.y - forehead.y;
                const noseRelativeY = (noseTip.y - forehead.y) / faceHeight;

                // Simple Iris gaze check relative to eye corners (Landmarks 33 to 133)
                const leftEyeOuter = landmarks[33];
                const leftEyeInner = landmarks[133];
                const eyeWidth = leftEyeInner.x - leftEyeOuter.x;
                const irisX = landmarks[468] ? landmarks[468].x : noseTip.x;
                const leftGaze = (irisX - leftEyeOuter.x) / eyeWidth;

                let state = "Looking at screen";

                // Eye and head posture classifications
                if (noseRelativeX < 0.38 || noseRelativeX > 0.62) {{
                    state = "Looking away";
                }} else if (noseRelativeY > 0.63) {{
                    state = "Reading from paper";
                }} else if (leftGaze < 0.32 || leftGaze > 0.68) {{
                    state = "Looking away";
                }}

                updatePythonState(state);
            }}

            const faceMesh = new FaceMesh({{locateFile: (file) => {{
                return `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${{file}}`;
            }}}});

            faceMesh.setOptions({{
                maxNumFaces: 1,
                refineLandmarks: true,
                minDetectionConfidence: 0.5,
                minTrackingConfidence: 0.5
            }});

            faceMesh.onResults(onResults);

            // Access user webcam — use front camera ('user') on mobile, any camera on desktop
            const videoConstraints = {{
                video: {{
                    facingMode: 'user',
                    width: {{ ideal: 320 }},
                    height: {{ ideal: 240 }}
                }}
            }};

            navigator.mediaDevices.getUserMedia(videoConstraints)
                .then(stream => {{
                    videoElement.srcObject = stream;
                    const camera = new Camera(videoElement, {{
                        onFrame: async () => {{
                            await faceMesh.send({{ image: videoElement }});
                        }},
                        width: 320,
                        height: 240
                    }});
                    camera.start();
                }})
                .catch(err => {{
                    console.error("Camera access blocked:", err);
                    // Show user-friendly error on mobile
                    document.getElementById('overlay').style.display = 'none';
                    errorMsg.style.display = 'block';
                    updatePythonState("Looking away");
                }});
        </script>
    </body>
    </html>
    """

