# XEMO

XEMO is my little robot person project.

It has two parts:

- gui/ is the phone and browser face. It handles the senses, conversation, memory, speech, goals, and the live brain view.
- bot/ is the local bridge plus the small-body firmware for the wheeled robot.

The idea is simple: XEMO should be able to notice things, talk naturally, remember what matters, choose small goals, and act carefully when the body is connected.

## What it uses

- a local OpenAI-compatible model server
- Kokoro for the story voice
- a browser for the face, camera, microphone, touch, and memory
- a small Wi-Fi robot body with wheels, arms, and distance sensing

## Run the browser app

Start the local bridge:

    ./scripts/run-web.sh

Then open the address printed by the bridge. The model server should be available at the local OpenAI-compatible endpoint, or set XEMO_BRAIN_URL.

## Body

The firmware expects MicroPython and the hardware modules in bot/. Copy the body files to the board, add a local secrets.py with Wi-Fi settings, and run firmware_main.py.

The pairing code is intentionally entered by the person using the app. It is not stored in this repository.

## Notes

XEMO keeps its personal memories in the browser that runs it. This repository contains the code, not anyone's private memories, pairing codes, local paths, or machine settings.
