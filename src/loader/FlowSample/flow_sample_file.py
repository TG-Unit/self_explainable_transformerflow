from typing import List, Tuple, Dict
from pathlib import Path
import pandas as pd
import numpy as np
import cv2 as cv
from copy import deepcopy

from ...datastructures.ArtificalGateDefinition import ArtificalGateDefinition

from ...utils.convex_hull_handler import convex_hull
from ...utils.outlier_handler import OutlierHandler

from ..GateCollection import GateCollection
from .flow_sample_base import FlowSampleBase
from ...datastructures.Gate import Gate
from ..IO.flowfileloader import FlowFileLoader
from ..MarkerCollection import MarkerCollection


class FlowSampleFile(FlowSampleBase):

    Artifical_gates_defintions : List[ArtificalGateDefinition] = []
    outlier_handler : OutlierHandler = None
    polygon_points : List[int] = [20]

    def __init__(self, file_path: Path) -> None:
        super().__init__()
        fileloader = FlowFileLoader(file_path)
        self.sample = fileloader.loadFlowMeData()
        self.sample_filename = file_path.parts[-1]
   
    def _getGateMarkerInfo(self) -> pd.DataFrame:

        metadata = self.sample.metadata()
        return metadata.gate_marker_info.replace(MarkerCollection.MARKER_DICT).replace(GateCollection.GATE_RENAME_DICT)

    def _getGatePolygonCoordinates(self) -> Tuple[str, List[List[float]]]:

        metadata = self.sample.metadata()
        return metadata.gate_polygons


# region [FlowSampleBase implementation]

    def get_gates(self) -> List[Gate]:

        result = []

        for (_, gate_marker_infp), (_, polygons_coors) in zip(self._getGateMarkerInfo().iterrows(), self._getGatePolygonCoordinates()):

            gate_name = gate_marker_infp["gate_name"]
            parentgate_name = gate_marker_infp["parent_name"]
            x_name = gate_marker_infp["x_axis_marker"]
            y_name = gate_marker_infp["y_axis_marker"]

            gate = Gate(gate_name, gate_name, parentgate_name, x_name,
                        y_name, np.array(polygons_coors))
            result.append(gate)

        return result

    def get_convex_gates(self) -> List[Gate]:

        events = self.get_events()
        labels = self.get_gate_labels()

        result = []

        for gate in FlowSampleFile.Artifical_gates_defintions:
            if gate.x_marker in events.columns and gate.y_marker in events.columns and gate.original_name in labels.columns:
                current_events = events.loc[:, [gate.x_marker, gate.y_marker]].copy()

                current_events = current_events[labels[gate.original_name] == 1]

                if FlowSampleFile.outlier_handler is not None and ("Blasts" in gate.original_name or "CD19" in gate.original_name):
                    #remove outliers
                    non_outlier_mask = FlowSampleFile.outlier_handler.get_non_outliers(current_events)
                    current_events = current_events[non_outlier_mask == True]

                scaled_events = current_events / 4.5

                events_convex_hull = convex_hull(np.array(scaled_events))
                result.append(Gate(gate.name, gate.original_name, gate.parent_name, gate.x_marker, gate.y_marker, events_convex_hull))

        return result

    def get_gate_labels(self) -> pd.DataFrame:
        gates = self.sample.gate_labels()
        gates = gates.loc[:, ~gates.columns.duplicated()].copy()
        return GateCollection.renameGates(gates)

    def get_events(self) -> pd.DataFrame:
        events = self.sample.events()
        return MarkerCollection.renameMarkers(events)

    def get_sample_name(self) -> str:
        metadata = self.sample.metadata()
        return metadata.exp_name

    def get_sample_file_name(self) -> str:
        return self.sample_filename

    def get_polygons_gates(self) -> Dict[int, Dict[str, np.ndarray]]:
        convex_gates = self.get_convex_gates()

        result = {}
        for points in FlowSampleFile.polygon_points:
            result[points] = {}

        for gate in convex_gates:
            for bbox_size in FlowSampleFile.polygon_points:
                poly = deepcopy(gate.polygon)
                while len(poly) < bbox_size:
                    l = len(poly)
                    distances = [np.linalg.norm(poly[i]-poly[(i+1)%l]) for i in range(l)]
                    maxIdx = np.argmax(distances)
                    newPoint = (poly[maxIdx] + poly[(maxIdx+1)%l])/2
                    poly = np.insert(poly, maxIdx+1, newPoint, axis=0)
                while len(poly) > bbox_size:
                    l = len(poly)
                    areas = [cv.contourArea(np.array([poly[(i-1)%l], poly[i], poly[(i+1)%l]])) for i in range(l)]
                    minArea = np.argmin(areas)
                    poly = np.delete(poly, minArea, axis=0)
                result[bbox_size][gate.name] = poly

        return result


# endregion
