"""
app/routers/alliances.py
Agent 5 — Développeur Backend | Sprint 4

GET    /alliances                    — liste des alliances (top 50 par score)
GET    /alliances/{id}               — détail alliance + membres
POST   /alliances                    — créer une alliance
POST   /alliances/{id}/join          — postuler à une alliance
POST   /alliances/{id}/members/{pid}/accept  — accepter une candidature
DELETE /alliances/{id}/members/{pid}         — expulser un membre / quitter
POST   /alliances/{id}/wars          — déclarer la guerre
DELETE /alliances/{id}/wars/{wid}    — déclarer la paix

Toutes les validations métier sont ici (pas de service séparé pour ce volume).
Les guards : leader only, officer+, membre only.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentPlayer, DbDep
from app.models.models import Alliance, Planet, Player
from app.models.alliance_models import AllianceMember, AllianceRole, AllianceWar, WarStatus
from app.core.redis_client import publish_event

router = APIRouter(prefix="/alliances", tags=["alliances"])

# GDD §alliances
_MAX_MEMBERS = 20
_MIN_SCORE_TO_CREATE = 500
_CREATE_COST_METAL = 10_000
_CREATE_COST_CRYSTAL = 5_000
_WAR_MIN_DURATION_HOURS = 48


# ─── Schemas ─────────────────────────────────────────────────────────────────

class AllianceSummary(BaseModel):
    id: str
    name: str
    tag: str
    score: int
    member_count: int
    leader_username: str

class MemberOut(BaseModel):
    player_id: str
    username: str
    role: str
    score: int
    joined_at: datetime

class WarOut(BaseModel):
    war_id: str
    opponent_name: str
    opponent_tag: str
    side: Literal["attacker", "defender"]
    declared_at: datetime
    status: str

class AllianceDetail(BaseModel):
    id: str
    name: str
    tag: str
    description: str | None
    score: int
    leader_id: str
    members: list[MemberOut]
    active_wars: list[WarOut]
    created_at: datetime

class CreateAllianceRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=32)
    tag:  str = Field(..., min_length=2, max_length=5, pattern="^[A-Z0-9]+$")
    description: str | None = Field(None, max_length=500)

class DeclareWarRequest(BaseModel):
    target_alliance_id: str


# ─── Helpers ─────────────────────────────────────────────────────────────────

async def _get_member(player_id: uuid.UUID, db) -> AllianceMember | None:
    r = await db.execute(select(AllianceMember).where(AllianceMember.player_id == player_id))
    return r.scalar_one_or_none()

async def _require_role(player_id: uuid.UUID, alliance_id: uuid.UUID, db,
                         min_role: AllianceRole = AllianceRole.MEMBER) -> AllianceMember:
    """Vérifie que le joueur est membre de l'alliance avec le rôle minimum requis."""
    r = await db.execute(
        select(AllianceMember).where(
            AllianceMember.player_id == player_id,
            AllianceMember.alliance_id == alliance_id,
        )
    )
    member = r.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=403, detail="Vous n'êtes pas membre de cette alliance.")

    role_order = {AllianceRole.MEMBER: 0, AllianceRole.OFFICER: 1, AllianceRole.LEADER: 2}
    if role_order.get(AllianceRole(member.role), 0) < role_order.get(min_role, 0):
        raise HTTPException(status_code=403, detail="Rôle insuffisant pour cette action.")
    return member


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("", response_model=list[AllianceSummary])
async def list_alliances(db: DbDep) -> list[AllianceSummary]:
    """Top 50 alliances par score. Public — pas d'auth requise."""
    result = await db.execute(
        select(Alliance).order_by(Alliance.score.desc()).limit(50)
    )
    alliances = result.scalars().all()

    out = []
    for a in alliances:
        # Compte des membres
        cnt = await db.execute(
            select(func.count(AllianceMember.id)).where(AllianceMember.alliance_id == a.id)
        )
        member_count = cnt.scalar() or 0

        # Nom du leader
        leader = await db.execute(select(Player).where(Player.id == a.leader_id))
        leader_player = leader.scalar_one_or_none()

        out.append(AllianceSummary(
            id=str(a.id),
            name=a.name,
            tag=a.tag,
            score=a.score,
            member_count=member_count,
            leader_username=leader_player.username if leader_player else "?",
        ))
    return out


@router.get("/{alliance_id}", response_model=AllianceDetail)
async def get_alliance(alliance_id: uuid.UUID, db: DbDep) -> AllianceDetail:
    """Détail d'une alliance avec membres et guerres actives."""
    result = await db.execute(select(Alliance).where(Alliance.id == alliance_id))
    alliance = result.scalar_one_or_none()
    if not alliance:
        raise HTTPException(status_code=404, detail="Alliance introuvable.")

    # Membres
    mems_result = await db.execute(
        select(AllianceMember).where(AllianceMember.alliance_id == alliance_id)
    )
    members_rows = mems_result.scalars().all()
    members_out = []
    for m in members_rows:
        p = await db.execute(select(Player).where(Player.id == m.player_id))
        player = p.scalar_one_or_none()
        if player:
            members_out.append(MemberOut(
                player_id=str(m.player_id),
                username=player.username,
                role=m.role,
                score=player.score,
                joined_at=m.joined_at,
            ))

    # Guerres actives
    wars_result = await db.execute(
        select(AllianceWar).where(
            (AllianceWar.attacker_id == alliance_id) | (AllianceWar.defender_id == alliance_id),
            AllianceWar.status == WarStatus.ACTIVE,
        )
    )
    wars_rows = wars_result.scalars().all()
    wars_out = []
    for w in wars_rows:
        is_attacker = w.attacker_id == alliance_id
        opponent_id = w.defender_id if is_attacker else w.attacker_id
        opp = await db.execute(select(Alliance).where(Alliance.id == opponent_id))
        opp_alliance = opp.scalar_one_or_none()
        if opp_alliance:
            wars_out.append(WarOut(
                war_id=str(w.id),
                opponent_name=opp_alliance.name,
                opponent_tag=opp_alliance.tag,
                side="attacker" if is_attacker else "defender",
                declared_at=w.declared_at,
                status=w.status,
            ))

    return AllianceDetail(
        id=str(alliance.id),
        name=alliance.name,
        tag=alliance.tag,
        description=alliance.description,
        score=alliance.score,
        leader_id=str(alliance.leader_id),
        members=members_out,
        active_wars=wars_out,
        created_at=alliance.created_at,
    )


@router.post("", response_model=AllianceDetail, status_code=status.HTTP_201_CREATED)
async def create_alliance(
    body: CreateAllianceRequest,
    player: CurrentPlayer,
    db: DbDep,
) -> AllianceDetail:
    """
    Crée une alliance. Le joueur devient automatiquement Leader.
    Coût : 10 000 métal + 5 000 cristal sur la planète natale.
    """
    # Vérification : pas déjà dans une alliance
    existing_member = await _get_member(player.id, db)
    if existing_member:
        raise HTTPException(status_code=409, detail="Vous êtes déjà membre d'une alliance.")

    # Score minimum
    if player.score < _MIN_SCORE_TO_CREATE:
        raise HTTPException(
            status_code=403,
            detail=f"Score insuffisant pour créer une alliance (min : {_MIN_SCORE_TO_CREATE})."
        )

    # Unicité du nom et du tag
    existing = await db.execute(
        select(Alliance).where(
            (Alliance.name == body.name) | (Alliance.tag == body.tag)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Ce nom ou tag d'alliance est déjà utilisé.")

    # Vérification et déduction ressources (planète natale)
    homeworld_result = await db.execute(
        select(Planet).where(Planet.owner_id == player.id, Planet.is_homeworld == True)  # noqa: E712
    )
    homeworld = homeworld_result.scalar_one_or_none()
    if not homeworld:
        raise HTTPException(status_code=404, detail="Planète natale introuvable.")
    if float(homeworld.metal) < _CREATE_COST_METAL or float(homeworld.crystal) < _CREATE_COST_CRYSTAL:
        raise HTTPException(
            status_code=402,
            detail=f"Ressources insuffisantes. Requis : {_CREATE_COST_METAL} métal, {_CREATE_COST_CRYSTAL} cristal."
        )

    homeworld.metal   = float(homeworld.metal)   - _CREATE_COST_METAL
    homeworld.crystal = float(homeworld.crystal) - _CREATE_COST_CRYSTAL
    db.add(homeworld)

    # Création de l'alliance
    new_alliance = Alliance(
        id=uuid.uuid4(),
        name=body.name,
        tag=body.tag,
        description=body.description,
        leader_id=player.id,
        score=player.score,
    )
    db.add(new_alliance)
    await db.flush()  # obtenir l'ID

    # Ajouter le créateur comme LEADER
    member = AllianceMember(
        id=uuid.uuid4(),
        alliance_id=new_alliance.id,
        player_id=player.id,
        role=AllianceRole.LEADER,
    )
    db.add(member)

    # Mettre à jour alliance_id du joueur
    player.alliance_id = new_alliance.id
    db.add(player)

    await db.commit()
    await db.refresh(new_alliance)

    # Retourner le détail
    return await get_alliance(new_alliance.id, db)


@router.post("/{alliance_id}/join", status_code=status.HTTP_200_OK)
async def join_alliance(
    alliance_id: uuid.UUID,
    player: CurrentPlayer,
    db: DbDep,
) -> dict:
    """
    Rejoindre une alliance (candidature — acceptée par leader/officer).
    Pour l'instant : admission directe si l'alliance a de la place.
    Phase 2 : système de candidature avec validation.
    """
    # Vérification : pas déjà membre
    if await _get_member(player.id, db):
        raise HTTPException(status_code=409, detail="Vous êtes déjà membre d'une alliance.")

    # Vérification alliance
    result = await db.execute(select(Alliance).where(Alliance.id == alliance_id))
    alliance = result.scalar_one_or_none()
    if not alliance:
        raise HTTPException(status_code=404, detail="Alliance introuvable.")

    # Vérification capacité
    cnt = await db.execute(
        select(func.count(AllianceMember.id)).where(AllianceMember.alliance_id == alliance_id)
    )
    if (cnt.scalar() or 0) >= _MAX_MEMBERS:
        raise HTTPException(status_code=409, detail="Cette alliance est complète (20 membres max).")

    member = AllianceMember(
        id=uuid.uuid4(),
        alliance_id=alliance_id,
        player_id=player.id,
        role=AllianceRole.MEMBER,
    )
    db.add(member)
    player.alliance_id = alliance_id
    db.add(player)
    await db.commit()

    return {"joined": True, "alliance_name": alliance.name, "tag": alliance.tag}


@router.delete("/{alliance_id}/members/{target_player_id}", status_code=204)
async def remove_member(
    alliance_id: uuid.UUID,
    target_player_id: uuid.UUID,
    player: CurrentPlayer,
    db: DbDep,
):
    """Quitter l'alliance (soi-même) ou expulser un membre (leader/officer)."""
    is_self = target_player_id == player.id

    if is_self:
        # Quitter — vérifier qu'on n'est pas le seul leader
        my_member = await _get_member(player.id, db)
        if not my_member or str(my_member.alliance_id) != str(alliance_id):
            raise HTTPException(status_code=403, detail="Vous n'êtes pas membre de cette alliance.")

        if my_member.role == AllianceRole.LEADER:
            # Vérifier s'il y a d'autres membres
            cnt = await db.execute(
                select(func.count(AllianceMember.id)).where(AllianceMember.alliance_id == alliance_id)
            )
            if (cnt.scalar() or 0) > 1:
                raise HTTPException(
                    status_code=409,
                    detail="Le leader ne peut pas quitter sans transférer le leadership ou dissoudre l'alliance."
                )
        target_member = my_member
    else:
        # Expulsion — vérifier le rôle
        await _require_role(player.id, alliance_id, db, AllianceRole.OFFICER)
        result = await db.execute(
            select(AllianceMember).where(
                AllianceMember.player_id == target_player_id,
                AllianceMember.alliance_id == alliance_id,
            )
        )
        target_member = result.scalar_one_or_none()
        if not target_member:
            raise HTTPException(status_code=404, detail="Membre introuvable.")

    await db.delete(target_member)

    # Mettre à jour alliance_id du joueur
    target_player = await db.execute(select(Player).where(Player.id == target_player_id))
    tp = target_player.scalar_one_or_none()
    if tp:
        tp.alliance_id = None
        db.add(tp)

    await db.commit()


@router.post("/{alliance_id}/wars", status_code=201)
async def declare_war(
    alliance_id: uuid.UUID,
    body: DeclareWarRequest,
    player: CurrentPlayer,
    db: DbDep,
) -> dict:
    """
    Déclare la guerre à une autre alliance.
    Seul le leader peut déclarer la guerre.
    Durée minimum : 48h avant de pouvoir déclarer la paix.
    """
    await _require_role(player.id, alliance_id, db, AllianceRole.LEADER)

    target_id = uuid.UUID(body.target_alliance_id)
    if target_id == alliance_id:
        raise HTTPException(status_code=400, detail="Impossible de se déclarer la guerre à soi-même.")

    # Vérifier qu'une guerre n'est pas déjà active
    existing_war = await db.execute(
        select(AllianceWar).where(
            ((AllianceWar.attacker_id == alliance_id) & (AllianceWar.defender_id == target_id)) |
            ((AllianceWar.attacker_id == target_id) & (AllianceWar.defender_id == alliance_id)),
            AllianceWar.status == WarStatus.ACTIVE,
        )
    )
    if existing_war.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Une guerre est déjà active entre ces deux alliances.")

    war = AllianceWar(
        id=uuid.uuid4(),
        attacker_id=alliance_id,
        defender_id=target_id,
        status=WarStatus.ACTIVE,
    )
    db.add(war)
    await db.commit()

    # Notifier les membres de l'alliance défenseure via WS
    mems = await db.execute(
        select(AllianceMember.player_id).where(AllianceMember.alliance_id == target_id)
    )
    attacker_alliance = await db.execute(select(Alliance).where(Alliance.id == alliance_id))
    attacker = attacker_alliance.scalar_one_or_none()

    for (pid,) in mems.all():
        await publish_event(str(pid), {
            "type": "alliance.war_declared",
            "data": {
                "war_id": str(war.id),
                "attacker_name": attacker.name if attacker else "?",
                "attacker_tag": attacker.tag if attacker else "?",
                "declared_at": war.declared_at.isoformat(),
            }
        })

    return {"war_id": str(war.id), "status": "ACTIVE", "min_peace_at": (war.declared_at + timedelta(hours=_WAR_MIN_DURATION_HOURS)).isoformat()}


@router.delete("/{alliance_id}/wars/{war_id}", status_code=200)
async def declare_peace(
    alliance_id: uuid.UUID,
    war_id: uuid.UUID,
    player: CurrentPlayer,
    db: DbDep,
) -> dict:
    """Déclare la paix (les deux leaders doivent accepter — phase 2)."""
    await _require_role(player.id, alliance_id, db, AllianceRole.LEADER)

    result = await db.execute(select(AllianceWar).where(AllianceWar.id == war_id))
    war = result.scalar_one_or_none()
    if not war:
        raise HTTPException(status_code=404, detail="Guerre introuvable.")

    # Vérifier durée minimum
    min_peace = war.declared_at + timedelta(hours=_WAR_MIN_DURATION_HOURS)
    if datetime.now(UTC) < min_peace.replace(tzinfo=UTC):
        raise HTTPException(
            status_code=409,
            detail=f"La paix ne peut être déclarée avant {min_peace.isoformat()} (48h minimum)."
        )

    war.status = WarStatus.PEACE
    war.peace_at = datetime.now(UTC)
    db.add(war)
    await db.commit()

    return {"war_id": str(war.id), "status": "PEACE"}
