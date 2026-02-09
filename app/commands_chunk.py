@command(Privileges.UNRESTRICTED, aliases=["recalculate"])
async def recalc(ctx: Context) -> str | None:
    """Recalculate your stats (pp, acc, etc) from your best scores."""
    # !recalc [mode] (default: current mode)
    if ctx.args:
        if ctx.args[0] not in GAMEMODE_REPR_LIST:
            return f"Valid gamemodes: {', '.join(GAMEMODE_REPR_LIST)}."
        mode = GameMode.from_params(GAMEMODE_REPR_LIST.index(ctx.args[0]), ctx.player.status.mods)
    else:
        mode = ctx.player.status.mode

    # Fetch all best scores for this mode
    scores = await app.state.services.database.fetch_all(
        "SELECT s.pp, s.acc, s.score, s.max_combo, s.n300, s.n100, s.n50, s.nmiss, s.ngeki, s.nkatu, s.grade "
        "FROM scores s "
        "WHERE s.userid = :user_id AND s.mode = :mode "
        "AND s.status = 2", # SubmissionStatus.BEST
        {"user_id": ctx.player.id, "mode": mode.value},
    )

    if not scores:
        return f"No best scores found for {mode!r}."

    # Recalculate stats
    stats = ctx.player.stats[mode]
    
    # Reset stats that will be recalculated
    # Note: plays and playtime are accumulative, so we might want to keep them 
    # or recalculate them if we trust the scores table fully. 
    # Usually plays/playtime are better left alone or updated incrementally, 
    # but tscore/rscore/pp/acc should be recalculated from best scores for consistency.
    # However, tscore/plays/playtime usually include failed/submitted scores too, not just best.
    # So we should ONLY recalculate PP, Acc, and Ranked Score from BEST scores.
    # Total Score, Plays, Playtime shouldn't be touched by this simple recalc 
    # unless we scan ALL scores (which is expensive).

    total_pp = 0.0
    total_rscore = 0
    weighted_acc = 0.0
    
    # Calculate PP and Acc
    # Sort by PP desc for weighting
    scores.sort(key=lambda s: s["pp"], reverse=True)
    
    for i, s in enumerate(scores):
        total_pp += s["pp"] * (0.95 ** i)
        weighted_acc += s["acc"] * (0.95 ** i)
        total_rscore += s["score"]

    bonus_pp = 416.6667 * (1 - 0.9994 ** len(scores))
    total_pp = round(total_pp + bonus_pp)
    
    bonus_acc = 100.0 / (20 * (1 - 0.95 ** len(scores)))
    final_acc = (weighted_acc * bonus_acc) / 100.0

    # Update stats object
    stats.pp = int(total_pp)
    stats.rscore = total_rscore
    stats.acc = final_acc
    
    # Update Grades (Optional, but good for consistency)
    # This might be tricky if we don't want to reset them. 
    # Let's skip grade recalculation for now to avoid issues, 
    # as grades are just counters.

    # Update Global/Country Rank
    stats.rank = await ctx.player.update_rank(mode)

    # Save to DB
    await users_repo.partial_update(
        ctx.player.id,
        mode.value,
        pp=stats.pp,
        rscore=stats.rscore,
        acc=stats.acc,
    )

    # Enqueue stats update to client
    app.state.sessions.players.enqueue(app.packets.user_stats(ctx.player))

    return f"Recalculated stats for {mode!r}: {stats.pp}pp, {stats.acc:.2f}%, #{stats.rank}"
