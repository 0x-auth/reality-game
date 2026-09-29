import HTML from "./index.html";
import {
  createGame, observe, advance, offerTrade, hypothesize, lock, view,
} from "./game.js";

// The front end is served from GitHub Pages, so this Worker is the realtime half
// only: one Durable Object per room, holding the single shared universe.

const CORS = {
  "access-control-allow-origin": "*",
  "access-control-allow-methods": "GET,OPTIONS",
  "access-control-allow-headers": "content-type",
};

export class Room {
  constructor(state) {
    this.state = state;
    this.game = createGame();
    this.seats = new Map(); // "A" | "B" -> WebSocket
  }

  async fetch(request) {
    if (request.headers.get("Upgrade") !== "websocket") {
      return new Response("expected websocket", { status: 426 });
    }

    const [client, server] = Object.values(new WebSocketPair());
    const seat = ["A", "B"].find((s) => !this.seats.has(s));

    server.accept();

    if (!seat) {
      server.send(JSON.stringify({ type: "error", error: "room_full" }));
      server.close(1013, "room full");
      return new Response(null, { status: 101, webSocket: client });
    }

    this.seats.set(seat, server);
    server.send(JSON.stringify({
      type: "joined",
      player_id: seat,
      axis: seat === "A" ? "cos" : "sin",
      state: this.view(seat),
    }));
    this.broadcast();

    server.addEventListener("message", (event) => {
      let message;
      try {
        message = JSON.parse(event.data);
      } catch {
        return server.send(JSON.stringify({ type: "error", error: "bad_json" }));
      }

      switch (message.action) {
        case "observe":     observe(this.game, seat); break;
        case "advance":     advance(this.game, seat); break;
        case "trade":       offerTrade(this.game, seat); break;
        case "hypothesize": hypothesize(this.game, seat, message.law); break;
        case "lock":        lock(this.game, seat); break;
        case "restart":     this.game = createGame(); break;
        default:
          return server.send(JSON.stringify({ type: "error", error: "unknown_action" }));
      }
      this.broadcast();
    });

    const drop = () => { this.seats.delete(seat); this.broadcast(); };
    server.addEventListener("close", drop);
    server.addEventListener("error", drop);

    return new Response(null, { status: 101, webSocket: client });
  }

  view(seat) {
    return view(this.game, seat, this.seats.size);
  }

  broadcast() {
    for (const [seat, socket] of this.seats) {
      try {
        socket.send(JSON.stringify({ type: "state", state: this.view(seat) }));
      } catch {
        this.seats.delete(seat);
      }
    }
  }
}

// Room codes a person can read aloud: no vowels, nothing that looks like 0/O or 1/I.
const ALPHABET = "BCDFGHJKLMNPQRSTVWXZ23456789";
const makeCode = () =>
  Array.from({ length: 4 }, () => ALPHABET[Math.floor(Math.random() * ALPHABET.length)]).join("");

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return new Response(null, { headers: CORS });
    }

    if (url.pathname === "/new") {
      return Response.json({ room: makeCode() }, { headers: CORS });
    }

    const ws = url.pathname.match(/^\/ws\/([A-Za-z0-9]{1,12})$/);
    if (ws) {
      const id = env.ROOM.idFromName(ws[1].toUpperCase());
      return env.ROOM.get(id).fetch(request);
    }

    return new Response(HTML, {
      headers: { "content-type": "text/html;charset=utf-8", "cache-control": "no-store" },
    });
  },
};
