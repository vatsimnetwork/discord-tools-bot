# Discord Tools Bot

Discord bot for miscellaneous tasks on the VATSIM Community server.

## Features

- `/charts` - ChartFox airport chart lookup
- `/metar` - VATSIM METAR and AVWX TAF
- `/screenshot` - post a screenshot as an embed
- Relays VATSIM network broadcasts from Kafka to a channel
- Posts VATSIM event and controller exam announcements

Command access is managed in Discord under Server Settings > Integrations.

## Configuration

Set via environment variables or a `.env` file. A missing required variable aborts startup.

| Variable | Default | Description |
| --- | --- | --- |
| `DISCORD_BOT_TOKEN` | required | Discord bot token |
| `AVWX_KEY` | required | AVWX API token, for TAFs in `/metar` |
| `CHARTFOX_KEY` | required | ChartFox API token, for `/charts` |
| `EVENTS_CHANNEL_ID` | unset | Event announcements. Unset stops them |
| `EXAMS_CHANNEL_ID` | unset | Controller exam announcements. Unset stops them |
| `NETWORK_BROADCASTS_CHANNEL_ID` | unset | Network broadcast relay. Unset stops it |
| `SCREENSHOT_VOTING_CHANNEL_ID` | unset | Channel where `/screenshot` adds an author header and a voting reaction. Unset gives every channel the plain embed |
| `NETWORK_KAFKA_SERVER` | empty | Broadcast Kafka bootstrap server |
| `NETWORK_KAFKA_USERNAME` | empty | Broadcast Kafka SASL username |
| `NETWORK_KAFKA_PASSWORD` | empty | Broadcast Kafka SASL password |
| `NETWORK_KAFKA_GROUP` | unset | Broadcast Kafka consumer group |
| `LOG_LEVEL` | `INFO` | Python logging level |

## Development

```sh
uv sync
uv run python run.py
uv run ruff check
uv run ruff format
```

## License

GNU Affero General Public License v3.0. See [LICENSE](LICENSE).
