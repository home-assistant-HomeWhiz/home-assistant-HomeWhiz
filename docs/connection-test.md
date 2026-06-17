# Bluetooth control / connection test

A small, self-contained Home Assistant test you can run on your own appliance to
check that **commands survive the periodic BLE reconnects** and that entities
**stay available** through them (the behaviour fixed for issue #367).

It repeatedly toggles a setting, waits for the appliance to reflect the change
back, and tallies pass/fail. Because it runs for a few minutes, some commands
land *during* a connection drop — which is exactly what we want to exercise.

## What you need to change for your appliance

The example targets a washing machine whose entities are prefixed
`*_washing_machine_*`. Replace these with your appliance's:

| Placeholder | What to use |
|---|---|
| `select.washing_machine_button_volume` | A **programme-independent** select on your appliance (button/key volume is ideal — the selected programme can't clamp it). Pick something with two stable options. |
| `volume_high` / `volume_low` | The two option values of that select (see the entity's `options` attribute in Developer Tools → States). |
| `binary_sensor.washing_machine_remote_control` | Your appliance's remote-control indicator. |

> Avoid using temperature/spin/rinse for the stress target: many programmes
> **clamp** those values (e.g. a delicates programme forces a lower temperature),
> so the read-back check fails even though the command was delivered — a false
> negative. A device setting like key volume can't be clamped.

## Before running

1. Put the appliance into **Remote Control** mode.
2. If you test a programme-dependent setting, also select a programme — but do
   **not** press Start. (On Beko machines, turning the dial exits remote mode;
   set the programme from HA via its `select.*_programme` entity instead.)

## Helpers (counters for the tally)

```yaml
# configuration.yaml
counter:
  homewhiz_test_pass:
    name: HomeWhiz Test Pass
    initial: 0
    step: 1
  homewhiz_test_fail:
    name: HomeWhiz Test Fail
    initial: 0
    step: 1
```

## Script

```yaml
# scripts.yaml  (or Settings → Automations & Scenes → Scripts → ⋮ → Edit in YAML)
homewhiz_volume_stress:
  alias: HomeWhiz volume stress test
  icon: mdi:volume-high
  mode: restart
  fields:
    cycles:
      name: Cycles
      default: 16
      selector:
        number:
          min: 1
          max: 100
          mode: box
  sequence:
    - action: counter.reset
      target:
        entity_id:
          - counter.homewhiz_test_pass
          - counter.homewhiz_test_fail
    - action: persistent_notification.create
      data:
        notification_id: homewhiz_test
        title: HomeWhiz volume stress
        message: >-
          Toggling button volume {{ cycles }} cycles over ~3 min, across BLE
          drops. Watch the entity stay available and listen for beeps.
    - repeat:
        count: "{{ cycles }}"
        sequence:
          - action: select.select_option
            continue_on_error: true
            target:
              entity_id: select.washing_machine_button_volume
            data:
              option: volume_high
          - wait_template: >-
              {{ is_state('select.washing_machine_button_volume', 'volume_high') }}
            timeout: { seconds: 15 }
            continue_on_timeout: true
          - if:
              - condition: template
                value_template: "{{ wait.completed }}"
            then:
              - action: counter.increment
                target: { entity_id: counter.homewhiz_test_pass }
            else:
              - action: counter.increment
                target: { entity_id: counter.homewhiz_test_fail }
              - action: logbook.log
                data:
                  name: HomeWhiz test
                  message: "FAIL cycle {{ repeat.index }}: volume_high not applied within 15s"
          - action: select.select_option
            continue_on_error: true
            target:
              entity_id: select.washing_machine_button_volume
            data:
              option: volume_low
          - wait_template: >-
              {{ is_state('select.washing_machine_button_volume', 'volume_low') }}
            timeout: { seconds: 15 }
            continue_on_timeout: true
          - if:
              - condition: template
                value_template: "{{ wait.completed }}"
            then:
              - action: counter.increment
                target: { entity_id: counter.homewhiz_test_pass }
            else:
              - action: counter.increment
                target: { entity_id: counter.homewhiz_test_fail }
              - action: logbook.log
                data:
                  name: HomeWhiz test
                  message: "FAIL cycle {{ repeat.index }}: volume_low not applied within 15s"
          - delay: { seconds: 4 }
    - action: persistent_notification.create
      data:
        notification_id: homewhiz_test
        title: HomeWhiz volume stress - done
        message: >-
          PASS: {{ states('counter.homewhiz_test_pass') }}   FAIL: {{
          states('counter.homewhiz_test_fail') }}. Any FAIL = a command that did
          not reach the appliance within 15s.
```

## Running and reading the result

1. Reload scripts (or restart HA) so the script/counters exist.
2. Run **`script.homewhiz_volume_stress`** (Settings → Scripts → Run).
3. When it finishes, the notification shows `PASS` / `FAIL`. Details for each
   failure are in **Settings → Logbook** (filter `HomeWhiz test`).

**Interpreting it:**

- **All / almost-all PASS** across the run = control is surviving the BLE drops.
- While it runs, confirm the entity **never shows `unavailable`** (check its
  history) — that's the availability debounce holding through the drops.
- A rare FAIL can happen if a command lands during an unusually long reconnect;
  a cluster of FAILs means commands are genuinely not getting through.
