"""Pure helpers for benchmark-only Gazebo ground-truth extraction."""


def select_robot_transform(transforms):
    """Return only the model transform for the SimInspect-X AMR, if present."""
    return next(
        (transform for transform in transforms
         if transform.child_frame_id == "siminspect_amr"),
        None,
    )
