import argparse
import time
from collections import OrderedDict, deque
import numpy as np
import cv2


class CentroidTracker:
    def __init__(self, maxDisappeared=40):
        self.nextObjectID = 0
        self.objects = OrderedDict()
        self.disappeared = OrderedDict()
        self.maxDisappeared = maxDisappeared

    def register(self, centroid):
        self.objects[self.nextObjectID] = centroid
        self.disappeared[self.nextObjectID] = 0
        self.nextObjectID += 1

    def deregister(self, objectID):
        del self.objects[objectID]
        del self.disappeared[objectID]

    def update(self, inputCentroids):
        if len(inputCentroids) == 0:
            for objectID in list(self.disappeared.keys()):
                self.disappeared[objectID] += 1
                if self.disappeared[objectID] > self.maxDisappeared:
                    self.deregister(objectID)
            return self.objects

        if len(self.objects) == 0:
            for c in inputCentroids:
                self.register(c)
        else:
            objectIDs = list(self.objects.keys())
            objectCentroids = list(self.objects.values())

            D = np.linalg.norm(np.array(objectCentroids)[:, None] - np.array(inputCentroids)[None, :], axis=2)

            rows = D.min(axis=1).argsort()
            cols = D.argmin(axis=1)[rows]

            usedRows = set()
            usedCols = set()

            for (row, col) in zip(rows, cols):
                if row in usedRows or col in usedCols:
                    continue
                objectID = objectIDs[row]
                self.objects[objectID] = inputCentroids[col]
                self.disappeared[objectID] = 0
                usedRows.add(row)
                usedCols.add(col)

            unusedRows = set(range(0, D.shape[0])).difference(usedRows)
            unusedCols = set(range(0, D.shape[1])).difference(usedCols)

            if D.shape[0] >= D.shape[1]:
                for row in unusedRows:
                    objectID = objectIDs[row]
                    self.disappeared[objectID] += 1
                    if self.disappeared[objectID] > self.maxDisappeared:
                        self.deregister(objectID)
            else:
                for col in unusedCols:
                    self.register(inputCentroids[col])

        return self.objects


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--source", default=0, help="camera index, video file or RTSP url")
    p.add_argument("--min-area", type=int, default=400, help="minimum contour area")
    p.add_argument("--width", type=int, default=400, help="resize width for processing")
    p.add_argument("--display", action="store_true", help="show video window")
    return p.parse_args()


def main():
    args = parse_args()

    src = args.source
    try:
        src = int(src)
    except Exception:
        pass

    cap = cv2.VideoCapture(src)
    time.sleep(1.0)

    fgbg = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=25, detectShadows=False)
    tracker = CentroidTracker(maxDisappeared=30)

    prev_centroids = {}
    counted = set()
    total_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        h, w = frame.shape[:2]
        r = args.width / float(w)
        frame = cv2.resize(frame, (args.width, int(h * r)))
        H, W = frame.shape[:2]

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        fg = fgbg.apply(gray)

        _, th = cv2.threshold(fg, 200, 255, cv2.THRESH_BINARY)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        th = cv2.morphologyEx(th, cv2.MORPH_OPEN, kernel, iterations=2)
        th = cv2.dilate(th, None, iterations=2)

        contours, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        rects = []
        centroids = []
        for c in contours:
            if cv2.contourArea(c) < args.min_area:
                continue
            x, y, ww, hh = cv2.boundingRect(c)
            rects.append((x, y, x + ww, y + hh))
            cx = int(x + ww / 2)
            cy = int(y + hh / 2)
            centroids.append((cx, cy))

        objects = tracker.update(centroids)

        line_y = H // 2
        cv2.line(frame, (0, line_y), (W, line_y), (0, 255, 255), 2)

        for objectID, centroid in objects.items():
            cX, cY = int(centroid[0]), int(centroid[1])
            previous = prev_centroids.get(objectID, None)
            if previous is not None:
                py = previous[1]
                if objectID not in counted:
                    if py < line_y and cY >= line_y:
                        total_count += 1
                        counted.add(objectID)
                    elif py > line_y and cY <= line_y:
                        total_count += 1
                        counted.add(objectID)

            prev_centroids[objectID] = (cX, cY)

            text = f"ID {objectID}"
            cv2.putText(frame, text, (cX - 10, cY - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
            cv2.circle(frame, (cX, cY), 4, (0, 255, 0), -1)

        cv2.putText(frame, f"Count: {total_count}", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        if args.display:
            cv2.imshow("people-counter", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
