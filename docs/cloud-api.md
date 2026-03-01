---
layout: default
title: Cloud API
nav_order: 8
description: "Yarbo cloud REST API reference for integration developers"
---

# Cloud API
{: .no_toc }

> **Disclaimer:** This is an independent community project. NOT affiliated with Yarbo or its manufacturer. API details are documented for integration development purposes.
{: .warning }

The Yarbo cloud REST API handles account management, robot binding, and supplementary data (maps, notifications, version info). The integration uses the local MQTT protocol for all real-time control; cloud API calls are used only for initial configuration and optional supplementary features.

1. TOC
{:toc}

---

## API Gateways

| Gateway | Purpose |
|---------|---------|
| `4zx17x5q7l.execute-api.us-east-1.amazonaws.com/Stage` | Main app API (all endpoints below, unless noted) |
| `26akbclmo9.execute-api.us-east-1.amazonaws.com/Stage` | MQTT migration service |

---

## Authentication

The API uses **Auth0 JWT (RS256)** bearer tokens obtained by logging in with your Yarbo account credentials.

### Login

**POST** `/yarbo/robot-service/robot/commonUser/login`

Request:
```json
{
  "username": "user@example.com",
  "password": "<base64-encoded RSA-encrypted password>"
}
```

Response:
```json
{
  "code": "00000",
  "success": true,
  "data": {
    "accessToken":  "<JWT — 30-day expiry>",
    "refreshToken": "<v1. refresh token>",
    "userId":       "user@example.com",
    "expiresIn":    2592000,
    "snList":       ["<robot_serial_number>"]
  }
}
```

The `accessToken` is used as `Authorization: Bearer <accessToken>` in all subsequent requests.

### Refresh Token

**POST** `/yarbo/robot-service/robot/commonUser/refreshToken`

Request body field: `refresh_token` (snake_case — not `refreshToken`).

```json
{ "refresh_token": "v1...." }
```

Returns a new `accessToken` and `refreshToken` with fresh expiry.

### Logout

**POST** `/yarbo/robot-service/robot/commonUser/logout`

Auth: Bearer token. Body: `{}`

---

## Common Response Envelope

All API responses share this structure:

```json
{
  "code":      "00000",
  "success":   true,
  "message":   "ok",
  "data":      { "...endpoint-specific..." },
  "sign":      "<RSA signature of response>",
  "timestamp": 1771934168898
}
```

| Code | Meaning |
|------|---------|
| `00000` | Success |
| `B0001` | Business error (message field contains details) |
| `A0230` | Authentication error |
| `400` | Bad request |

---

## Robot Management

### List Bound Robots

**GET** `/yarbo/robot-service/commonUser/userRobotBind/getUserRobotBindVos`

Auth: Bearer token.

Response `data`:
```json
{
  "deviceList": [
    {
      "serialNum":      "24400102L8HO5227",
      "headType":       1,
      "master":         1,
      "masterUsername": "user@example.com",
      "deviceNickname": "Allgott",
      "gmtCreate":      "2026-02-24 13:47:48"
    }
  ]
}
```

| Field | Description |
|-------|-------------|
| `serialNum` | Robot serial number |
| `headType` | Currently installed head type (0 = none, 1 = snow blower, etc.) |
| `master` | `1` = you are the primary owner; `0` = shared access |
| `masterUsername` | Email of the primary owner |
| `deviceNickname` | Robot friendly name |

### Rename Robot

**POST** `/yarbo/robot-service/robot/commonUser/updateSnowbotName`

Auth: Bearer token.

```json
{ "sn": "24400102L8HO5227", "name": "My Yarbo" }
```

### Bind a Robot

**POST** `/yarbo/robot-service/robot/commonUser/bindUserRobot`

Auth: Bearer token.

```json
{ "sn": "24400102L8HO5227" }
```

### Unbind a Robot

**POST** `/yarbo/robot-service/commonUser/userRobotBind/unbind`

Auth: Bearer token.

```json
{ "serialNums": ["24400102L8HO5227"] }
```

---

## Warranty Information

### Get Warranty Status

**POST** `/yarbo/robot-service/robot/commonUser/getWarrantyInfo`

Auth: Bearer token.

```json
{ "sn": "24400102L8HO5227" }
```

Response `data.list`:
```json
[
  {
    "sn":          "24400102L8HO5227",
    "module_type": 0,
    "regist_ts":   1767716871,
    "regied_ts":   1830788871,
    "in_warranty": true,
    "update_time": 1767716871
  }
]
```

| Field | Description |
|-------|-------------|
| `module_type` | `0` = main body; `1` = head attachment |
| `regist_ts` | Registration timestamp (Unix seconds) |
| `regied_ts` | Warranty expiry timestamp (Unix seconds) |
| `in_warranty` | Currently within warranty |

---

## Map / Raster Background

### Get Map Background

**GET** `/yarbo/robot/rasterBackground/get?sn=<SN>`

Auth: Bearer token.

Returns a pre-signed S3 URL (valid ~60 seconds) for the yard satellite map image (PNG).

Response `data`:
```json
{
  "accessUrl":   "https://yarbo-commonuser.s3.amazonaws.com/...",
  "object_data": "{\"top_left_real\":{...},\"center_real\":{...},\"rad\":0.049}",
  "gmt_modified": "2026-01-11T19:04:12.259375"
}
```

`object_data` is a double-encoded JSON string with geospatial metadata in the robot's local coordinate frame.

### Upload Map Background

**POST** `/yarbo/robot/rasterBackground/add`

Auth: Bearer token.

```json
{ "sn": "24400102L8HO5227", "imageData": "<base64-encoded PNG>" }
```

---

## Notifications

### Get Notification Settings

**GET** `/yarbo/msg/getNotificationSetting`

Auth: Bearer token.

Response `data`:
```json
{
  "mobileSystemNotification": 1,
  "generalNotification":      1,
  "errNotification":          1
}
```

Values: `1` = enabled, `0` = disabled.

### Update Notification Settings

**POST** `/yarbo/msg/updateNotificationSetting`

Auth: Bearer token.

```json
{
  "mobileSystemNotification": 1,
  "generalNotification":      0,
  "errNotification":          1
}
```

### Get Device Messages

**GET** `/yarbo/msg/userDeviceMsg`

Auth: Bearer token.

Returns device-level alerts and status messages.

---

## Robot Sharing (Whitelist)

### List Shared Users

**GET** `/yarbo/robot-service/commonUser/userWhiteList/getUserWhiteList`

Auth: Bearer token. Optional query: `?sn=<SN>`

Response `data.userWhiteLists` is an array of shared user entries.

### Invite a User

**POST** `/yarbo/robot-service/commonUser/userWhiteList/sendWhiteListInvitationEmail`

Auth: Bearer token.

```json
{ "email": "friend@example.com", "sn": "24400102L8HO5227" }
```

### Remove a Shared User

**POST** `/yarbo/robot-service/commonUser/userWhiteList/removeUserOfWhiteList`

Auth: Bearer token.

```json
{ "email": "friend@example.com", "sn": "24400102L8HO5227" }
```

---

## Version Information

### Get Latest Versions

**GET** `/yarbo/commonUser/getLatestPubVersion`

Auth: Bearer token.

Response `data`:
```json
{
  "appVersion":          "3.16.3",
  "firmwareVersion":     "3.11.0",
  "firmwareDescription": "New Features:\n1. Smart Vision...",
  "dcVersion":           "1.0.25",
  "dcDescription":       "Improvements..."
}
```

---

## MQTT Migration Status

### Check Migration Status

**GET** `https://26akbclmo9.execute-api.us-east-1.amazonaws.com/Stage/yarbo/mqtt-migration/query?sn=<SN>`

Auth: **None required.** Open endpoint.

Response `data`:
```json
{ "migrated": false }
```

`migrated: false` = robot uses Tencent TDMQ as its cloud MQTT broker.
`migrated: true` = robot has migrated to a newer broker.

---

## Live Video (Agora)

### Get Agora Token

**POST** `/yarbo/robot-service/robot/commonUser/getAgoraToken`

Auth: Bearer token.

Note: field name is `channel_name` (snake_case).

```json
{ "sn": "24400102L8HO5227", "channel_name": "my_channel" }
```

Returns an Agora RTC token and app configuration for live video streaming from the robot's camera.

---

## User Profile

### Update Profile

**POST** `/yarbo/robot-service/robot/commonUser/updateUserInfo`

Auth: Bearer token.

```json
{ "nickName": "My Name" }
```

### Download Avatar

**GET** `/yarbo/robot-service/robot/commonUser/downloadUserAvatar`

Auth: Bearer token. Returns `{"avatarBase64": "<base64 data or empty string>"}`.

---

## Auth Summary

| Endpoint group | Auth required |
|---------------|---------------|
| Login / Register | None |
| Token refresh | None |
| Robot management | Bearer JWT |
| User profile | Bearer JWT (some routes require additional privileges) |
| Notification settings | Bearer JWT |
| Robot sharing | Bearer JWT |
| Map operations | Bearer JWT |
| Version check | Bearer JWT |
| MQTT migration query | None (open endpoint) |

---

## Related Pages

- [Communication Architecture](communication-architecture.md) — how cloud and local paths interact
- [Protocol Reference](protocol-reference.md) — local MQTT protocol
- [Getting Started](getting-started.md) — installation guide
