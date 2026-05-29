class Handler:
    def save(self, value):
        return "saved:%s" % value


def audit(value):
    return f"audit:{value}"


def run_dynamic_gap_sample(handler_name, payload):
    handler = Handler()
    method = getattr(handler, handler_name)
    first_result = method(payload)

    callbacks = {
        "audit": audit,
        "inline": lambda item: "inline {}".format(item),
    }
    selected = callbacks["audit"]
    second_result = selected(first_result)

    query = "payload=%s" % payload
    message = "payload {}".format(payload)
    summary = f"{message}:{second_result}"

    list(map(audit, [payload]))
    return query, message, summary
