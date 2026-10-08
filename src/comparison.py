"""Summary fields used by strict and witness-independent semantic replay."""


def project_summary(summary, mode):
    if mode not in ("semantic", "strict"):
        raise ValueError("unknown comparison mode")
    if mode == "strict":
        return dict(summary)
    return {key: value for key, value in summary.items()
            if key != "max_certificate_bytes"}
