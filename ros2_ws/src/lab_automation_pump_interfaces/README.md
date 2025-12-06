# lab_automation_pump_interfaces

This package contains the message and action definitions for the `lab_automation_pump` package.

## Messages

### `PumpState.msg`

This message contains the current state of the pump.

```
bool state
int32 speed
bool dir
string last_step
builtin_interfaces/Time stamp
```

- `state`: The current state of the pump (on/off).
- `speed`: The current speed of the pump.
- `dir`: The current direction of the pump.
- `last_step`: The last step performed by the pump.
- `stamp`: The timestamp of the message.

## Actions

### `PumpStep.action`

This action defines a step for the pump to perform.

#### Goal

```
bool state
int32 speed
bool dir
int32 duration_ms
```

- `state`: The desired state of the pump (on/off).
- `speed`: The desired speed of the pump.
- `dir`: The desired direction of the pump.
- `duration_ms`: The duration of the step in milliseconds.

#### Result

```
bool success
string message
```

- `success`: Whether the step was successful.
- `message`: A message describing the result.

#### Feedback

```
float32 elapsed_s
float32 progress
string detail
```

- `elapsed_s`: The elapsed time in seconds.
- `progress`: The progress of the step (0.0 to 1.0).
- `detail`: A message describing the current progress.
