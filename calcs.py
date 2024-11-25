def camera_height(
        viewport_scale,
        distance_from_subject,
        width_of_base
):
    """
    Calculate how high off the ground the camera needs to
    be in order to most efficiently capture the base of your
    subject.
    """
    return (
        viewport_scale +
        distance_from_subject -
        (width_of_base * (2.0 ** -0.5))
    ) / (3.0 ** 0.5)
