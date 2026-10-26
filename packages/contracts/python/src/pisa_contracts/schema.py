# Generated from packages/contracts/schema/pisa.schema.json by `make gen`. Do not edit by hand.
# ruff: noqa: E501
"""The contracts' JSON Schema, for code that passes it on, such as the planner's output format."""

import json
from typing import Any

SCHEMA: dict[str, Any] = json.loads(
    r"""
{
 "$schema": "https://json-schema.org/draft/2020-12/schema",
 "$id": "urn:pisa:contracts:0.1.0",
 "title": "PisaContracts",
 "description": "Shared contracts between the Pisa engine (Python) and web app (TypeScript). Conventions: every property is required and optional values are nullable; times are in seconds, lengths in meters, image coordinates in pixels with the origin at the top-left and y pointing down.",
 "type": "object",
 "additionalProperties": false,
 "properties": {},
 "$defs": {
  "Locale": {
   "type": "string",
   "enum": [
    "en",
    "es",
    "zh-CN",
    "pt-BR"
   ]
  },
  "JobSource": {
   "type": "string",
   "enum": [
    "web",
    "whatsapp",
    "eval"
   ]
  },
  "DataPolicy": {
   "description": "user: a video someone submitted; never sent to a contributor-tier model. internal: our own test clips; contributor tier allowed.",
   "type": "string",
   "enum": [
    "user",
    "internal"
   ]
  },
  "Stage": {
   "type": "string",
   "enum": [
    "ingest",
    "plan",
    "track",
    "stabilize",
    "measure",
    "test",
    "verdict",
    "explain",
    "render"
   ]
  },
  "JobStatus": {
   "type": "string",
   "enum": [
    "queued",
    "running",
    "done",
    "failed"
   ]
  },
  "ErrorInfo": {
   "description": "A user-facing error. The client localizes `code`; no free text crosses the boundary.",
   "type": "object",
   "additionalProperties": false,
   "required": [
    "code",
    "stage"
   ],
   "properties": {
    "code": {
     "type": "string",
     "examples": [
      "video_too_long",
      "unsupported_format"
     ]
    },
    "stage": {
     "anyOf": [
      {
       "$ref": "#/$defs/Stage"
      },
      {
       "type": "null"
      }
     ]
    }
   }
  },
  "Job": {
   "type": "object",
   "additionalProperties": false,
   "required": [
    "id",
    "created_at",
    "source",
    "locale",
    "data_policy",
    "status",
    "stage",
    "error"
   ],
   "properties": {
    "id": {
     "type": "string",
     "format": "uuid"
    },
    "created_at": {
     "type": "string",
     "format": "date-time"
    },
    "source": {
     "$ref": "#/$defs/JobSource"
    },
    "locale": {
     "$ref": "#/$defs/Locale"
    },
    "data_policy": {
     "$ref": "#/$defs/DataPolicy"
    },
    "status": {
     "$ref": "#/$defs/JobStatus"
    },
    "stage": {
     "description": "The stage running now, or the last one reached.",
     "anyOf": [
      {
       "$ref": "#/$defs/Stage"
      },
      {
       "type": "null"
      }
     ]
    },
    "error": {
     "anyOf": [
      {
       "$ref": "#/$defs/ErrorInfo"
      },
      {
       "type": "null"
      }
     ]
    }
   }
  },
  "VideoProbe": {
   "description": "What ffprobe reports about a video file.",
   "type": "object",
   "additionalProperties": false,
   "required": [
    "width",
    "height",
    "duration_s",
    "fps_num",
    "fps_den",
    "is_vfr",
    "rotation_deg",
    "frame_count",
    "codec",
    "has_audio",
    "size_bytes"
   ],
   "properties": {
    "width": {
     "type": "integer",
     "minimum": 1,
     "description": "Display width after rotation."
    },
    "height": {
     "type": "integer",
     "minimum": 1,
     "description": "Display height after rotation."
    },
    "duration_s": {
     "type": "number",
     "minimum": 0
    },
    "fps_num": {
     "type": "integer",
     "minimum": 1,
     "description": "Average frame rate numerator."
    },
    "fps_den": {
     "type": "integer",
     "minimum": 1,
     "description": "Average frame rate denominator."
    },
    "is_vfr": {
     "type": "boolean",
     "description": "True when the stream's frame rate is variable."
    },
    "rotation_deg": {
     "type": "integer",
     "description": "Display rotation from the container, in degrees."
    },
    "frame_count": {
     "type": [
      "integer",
      "null"
     ],
     "minimum": 0
    },
    "codec": {
     "type": "string"
    },
    "has_audio": {
     "type": "boolean"
    },
    "size_bytes": {
     "type": "integer",
     "minimum": 0
    }
   }
  },
  "Timebase": {
   "description": "Maps frame indices of a constant-frame-rate clip to time: t(frame) = start_s + frame * fps_den / fps_num.",
   "type": "object",
   "additionalProperties": false,
   "required": [
    "fps_num",
    "fps_den",
    "start_s",
    "frame_count"
   ],
   "properties": {
    "fps_num": {
     "type": "integer",
     "minimum": 1
    },
    "fps_den": {
     "type": "integer",
     "minimum": 1
    },
    "start_s": {
     "type": "number",
     "minimum": 0,
     "description": "Time of frame 0 in the source video."
    },
    "frame_count": {
     "type": "integer",
     "minimum": 0
    }
   }
  },
  "IngestResult": {
   "type": "object",
   "additionalProperties": false,
   "required": [
    "source",
    "normalized",
    "timebase",
    "scene_cuts_s"
   ],
   "properties": {
    "source": {
     "$ref": "#/$defs/VideoProbe"
    },
    "normalized": {
     "$ref": "#/$defs/VideoProbe"
    },
    "timebase": {
     "$ref": "#/$defs/Timebase"
    },
    "scene_cuts_s": {
     "type": "array",
     "items": {
      "type": "number"
     }
    }
   },
   "description": "Probe of the source file and of the normalized H.264 MP4 at a constant frame rate that every later stage reads."
  },
  "EventType": {
   "type": "string",
   "enum": [
    "fall",
    "throw",
    "bounce",
    "pair_drop"
   ]
  },
  "CameraMotion": {
   "type": "string",
   "enum": [
    "static",
    "handheld",
    "pan",
    "unknown"
   ]
  },
  "PlanEvent": {
   "description": "One physical event the planner saw in the clip.",
   "type": "object",
   "additionalProperties": false,
   "required": [
    "type",
    "start_s",
    "end_s",
    "object_phrases"
   ],
   "properties": {
    "type": {
     "$ref": "#/$defs/EventType"
    },
    "start_s": {
     "type": "number",
     "description": "When the event starts, in seconds from the start of the clip."
    },
    "end_s": {
     "type": "number",
     "description": "When the event ends, in seconds from the start of the clip."
    },
    "object_phrases": {
     "description": "Short concrete noun phrases for the moving objects, one object each, for example \"tennis ball\". Two phrases for a pair drop.",
     "type": "array",
     "items": {
      "type": "string"
     }
    }
   }
  },
  "ReferenceObject": {
   "description": "An object of roughly known size near the plane of motion, used to convert pixels to meters.",
   "type": "object",
   "additionalProperties": false,
   "required": [
    "phrase",
    "dimension",
    "size_min_m",
    "size_max_m"
   ],
   "properties": {
    "phrase": {
     "type": "string",
     "description": "Short concrete noun phrase, for example \"door\"."
    },
    "dimension": {
     "type": "string",
     "enum": [
      "height",
      "width",
      "diameter",
      "length"
     ]
    },
    "size_min_m": {
     "type": "number",
     "description": "Smallest plausible real size in meters."
    },
    "size_max_m": {
     "type": "number",
     "description": "Largest plausible real size in meters."
    }
   }
  },
  "CameraNotes": {
   "type": "object",
   "additionalProperties": false,
   "required": [
    "motion",
    "has_cuts",
    "slow_motion_suspected"
   ],
   "properties": {
    "motion": {
     "$ref": "#/$defs/CameraMotion"
    },
    "has_cuts": {
     "type": "boolean"
    },
    "slow_motion_suspected": {
     "type": "boolean"
    }
   }
  },
  "PlanReason": {
   "description": "Why nothing in a clip can be measured. no_free_flight: nothing falls, flies or bounces on its own (objects are carried, pushed, self-propelled, or still). too_unclear: something does, but it is too small, blurred, hidden, brief or cut to follow.",
   "type": "string",
   "enum": [
    "no_free_flight",
    "too_unclear"
   ]
  },
  "Plan": {
   "description": "The planner's reading of a clip. Sent as a structured-output schema, so it stays inside Muse Spark's strict subset: no oneOf or allOf, every object closed, every key required.",
   "type": "object",
   "additionalProperties": false,
   "required": [
    "measurable",
    "reason",
    "events",
    "references",
    "camera"
   ],
   "properties": {
    "measurable": {
     "type": "boolean",
     "description": "False when nothing in the clip can be measured."
    },
    "reason": {
     "description": "Why nothing is measurable, when measurable is false.",
     "anyOf": [
      {
       "$ref": "#/$defs/PlanReason"
      },
      {
       "type": "null"
      }
     ]
    },
    "events": {
     "type": "array",
     "items": {
      "$ref": "#/$defs/PlanEvent"
     }
    },
    "references": {
     "type": "array",
     "items": {
      "$ref": "#/$defs/ReferenceObject"
     }
    },
    "camera": {
     "$ref": "#/$defs/CameraNotes"
    }
   }
  },
  "BBox": {
   "type": "object",
   "additionalProperties": false,
   "required": [
    "x1",
    "y1",
    "x2",
    "y2"
   ],
   "properties": {
    "x1": {
     "type": "number"
    },
    "y1": {
     "type": "number"
    },
    "x2": {
     "type": "number"
    },
    "y2": {
     "type": "number"
    }
   }
  },
  "Point2": {
   "type": "object",
   "additionalProperties": false,
   "required": [
    "x",
    "y"
   ],
   "properties": {
    "x": {
     "type": "number"
    },
    "y": {
     "type": "number"
    }
   }
  },
  "TrackSample": {
   "type": "object",
   "additionalProperties": false,
   "required": [
    "frame",
    "t_s",
    "bbox",
    "centroid",
    "area_px",
    "confidence"
   ],
   "properties": {
    "frame": {
     "type": "integer",
     "minimum": 0,
     "description": "Frame index in the normalized clip."
    },
    "t_s": {
     "type": "number",
     "description": "Time from the timebase."
    },
    "bbox": {
     "$ref": "#/$defs/BBox"
    },
    "centroid": {
     "$ref": "#/$defs/Point2"
    },
    "area_px": {
     "type": "number",
     "minimum": 0
    },
    "confidence": {
     "type": [
      "number",
      "null"
     ],
     "minimum": 0,
     "maximum": 1
    }
   },
   "description": "One tracked object in one frame. centroid is the mask centroid and area_px the mask area, both in pixels."
  },
  "TrackedObject": {
   "type": "object",
   "additionalProperties": false,
   "required": [
    "phrase",
    "object_id",
    "samples"
   ],
   "properties": {
    "phrase": {
     "type": "string"
    },
    "object_id": {
     "type": "integer",
     "minimum": 0,
     "description": "SAM's id, unique within one phrase."
    },
    "samples": {
     "type": "array",
     "items": {
      "$ref": "#/$defs/TrackSample"
     }
    }
   }
  },
  "TrackSet": {
   "type": "object",
   "additionalProperties": false,
   "required": [
    "width",
    "height",
    "timebase",
    "objects"
   ],
   "properties": {
    "width": {
     "type": "integer",
     "minimum": 1
    },
    "height": {
     "type": "integer",
     "minimum": 1
    },
    "timebase": {
     "$ref": "#/$defs/Timebase"
    },
    "objects": {
     "type": "array",
     "items": {
      "$ref": "#/$defs/TrackedObject"
     }
    }
   }
  },
  "TestId": {
   "description": "T1 free_fall_shape, T2 galileo_pair, T3 bounce_energy, T4 implied_g, T5 time_base_consistency.",
   "type": "string",
   "enum": [
    "free_fall_shape",
    "galileo_pair",
    "bounce_energy",
    "implied_g",
    "time_base_consistency"
   ]
  },
  "TestOutcome": {
   "type": "string",
   "enum": [
    "pass",
    "violation",
    "insufficient_data",
    "not_applicable"
   ]
  },
  "Measurement": {
   "description": "A number the explainer is allowed to quote.",
   "type": "object",
   "additionalProperties": false,
   "required": [
    "name",
    "value",
    "unit",
    "ci_low",
    "ci_high"
   ],
   "properties": {
    "name": {
     "type": "string",
     "examples": [
      "implied_g",
      "acceleration_ratio"
     ]
    },
    "value": {
     "type": "number"
    },
    "unit": {
     "type": "string",
     "description": "SI unit, or \"1\" when dimensionless.",
     "examples": [
      "m/s^2",
      "1"
     ]
    },
    "ci_low": {
     "type": [
      "number",
      "null"
     ]
    },
    "ci_high": {
     "type": [
      "number",
      "null"
     ]
    }
   }
  },
  "TestResult": {
   "type": "object",
   "additionalProperties": false,
   "required": [
    "test",
    "outcome",
    "confidence",
    "measurements",
    "reason_code"
   ],
   "properties": {
    "test": {
     "$ref": "#/$defs/TestId"
    },
    "outcome": {
     "$ref": "#/$defs/TestOutcome"
    },
    "confidence": {
     "type": "number",
     "minimum": 0,
     "maximum": 1
    },
    "measurements": {
     "type": "array",
     "items": {
      "$ref": "#/$defs/Measurement"
     }
    },
    "reason_code": {
     "type": [
      "string",
      "null"
     ]
    }
   }
  },
  "VerdictLabel": {
   "type": "string",
   "enum": [
    "physically_impossible",
    "consistent_with_real_physics",
    "inconclusive"
   ]
  },
  "Verdict": {
   "type": "object",
   "additionalProperties": false,
   "required": [
    "label",
    "policy_version",
    "decisive_tests",
    "reason_code"
   ],
   "properties": {
    "label": {
     "$ref": "#/$defs/VerdictLabel"
    },
    "policy_version": {
     "type": "string"
    },
    "decisive_tests": {
     "type": "array",
     "items": {
      "$ref": "#/$defs/TestId"
     }
    },
    "reason_code": {
     "type": [
      "string",
      "null"
     ],
     "description": "Why the verdict is inconclusive, when it is."
    }
   }
  },
  "CostUnit": {
   "type": "string",
   "enum": [
    "input_tokens",
    "output_tokens",
    "frames"
   ]
  },
  "CostEntry": {
   "type": "object",
   "additionalProperties": false,
   "required": [
    "stage",
    "model",
    "unit",
    "quantity",
    "usd"
   ],
   "properties": {
    "stage": {
     "$ref": "#/$defs/Stage"
    },
    "model": {
     "type": "string"
    },
    "unit": {
     "$ref": "#/$defs/CostUnit"
    },
    "quantity": {
     "type": "number",
     "minimum": 0
    },
    "usd": {
     "type": "number",
     "minimum": 0
    }
   }
  },
  "Stabilization": {
   "description": "How camera motion was handled before measuring. Unreliable frames are dropped; cuts are in the ingest result.",
   "type": "object",
   "additionalProperties": false,
   "required": [
    "applied",
    "max_motion_px",
    "frames",
    "unreliable_frames"
   ],
   "properties": {
    "applied": {
     "type": "boolean",
     "description": "False when the camera was still, or the background had nothing to follow."
    },
    "max_motion_px": {
     "type": "number",
     "minimum": 0,
     "description": "Largest displacement of a frame corner relative to the first frame of its shot."
    },
    "frames": {
     "type": "integer",
     "minimum": 0
    },
    "unreliable_frames": {
     "type": "integer",
     "minimum": 0
    }
   }
  },
  "Explanation": {
   "description": "A short explanation of the verdict in the job's language, written by Muse Spark from the measurements. Every number in it was checked against them; when the check fails there is no explanation and clients use their own templated copy.",
   "type": "object",
   "additionalProperties": false,
   "required": [
    "locale",
    "text",
    "model"
   ],
   "properties": {
    "locale": {
     "$ref": "#/$defs/Locale"
    },
    "text": {
     "type": "string"
    },
    "model": {
     "type": "string"
    }
   }
  },
  "AnalysisResult": {
   "description": "Everything the result page and the WhatsApp reply need for one job.",
   "type": "object",
   "additionalProperties": false,
   "required": [
    "job",
    "ingest",
    "plan",
    "tracks",
    "stabilization",
    "tests",
    "verdict",
    "explanation",
    "costs"
   ],
   "properties": {
    "job": {
     "$ref": "#/$defs/Job"
    },
    "ingest": {
     "anyOf": [
      {
       "$ref": "#/$defs/IngestResult"
      },
      {
       "type": "null"
      }
     ]
    },
    "plan": {
     "anyOf": [
      {
       "$ref": "#/$defs/Plan"
      },
      {
       "type": "null"
      }
     ]
    },
    "tracks": {
     "anyOf": [
      {
       "$ref": "#/$defs/TrackSet"
      },
      {
       "type": "null"
      }
     ]
    },
    "stabilization": {
     "anyOf": [
      {
       "$ref": "#/$defs/Stabilization"
      },
      {
       "type": "null"
      }
     ]
    },
    "tests": {
     "type": "array",
     "items": {
      "$ref": "#/$defs/TestResult"
     }
    },
    "verdict": {
     "anyOf": [
      {
       "$ref": "#/$defs/Verdict"
      },
      {
       "type": "null"
      }
     ]
    },
    "explanation": {
     "anyOf": [
      {
       "$ref": "#/$defs/Explanation"
      },
      {
       "type": "null"
      }
     ]
    },
    "costs": {
     "type": "array",
     "items": {
      "$ref": "#/$defs/CostEntry"
     }
    }
   }
  }
 }
}
"""
)
