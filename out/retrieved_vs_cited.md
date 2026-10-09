# Retrieved vs Cited — one ChatGPT query

- **Fan-out sub-queries issued:** 2
- **Sources retrieved:** 25
- **Sources cited in the final answer:** 7
- **Retrieved -> cited conversion:** 28%
- **Citation (`type: cite`) objects:** 18
- **YouTube sources retrieved:** 2 (cited: 1)
- **ref_type distribution:** search=21, youtube=2, reddit=2
- **Transcript-shaped keys in raw stream:** NONE

## Fan-out queries

The UI never displays these; they exist only in the stream.

1. `best project management tools for small agencies 2026 comparison pricing features Asana ClickUp Monday Teamwork Basecamp`
2. `YouTube project management software review 2026 small agency ClickUp Asana Teamwork Monday.com`

## YouTube field audit

Fields the "ChatGPT Retrieval Leak" writeup reports for YouTube sources, checked against this capture:

| claimed field | on a YouTube entry | key anywhere in stream | context if found |
|---|---|---|---|
| `channel` | no | YES | `3-206a1404a3a7","model_switcher_deny":[]},"recipient":"all","channel":` |
| `channel_name` | no | no |  |
| `followers` | no | no |  |
| `follower_count` | no | no |  |
| `subscribers` | no | no |  |
| `subscriber_count` | no | no |  |
| `verified` | no | no |  |
| `is_verified` | no | no |  |
| `views` | no | no |  |
| `view_count` | no | no |  |
| `likes` | no | no |  |
| `like_count` | no | no |  |
| `description` | no | no |  |
| `transcript` | no | no |  |

Keys actually present on YouTube entries: `attribution`, `cite_refs`, `cited`, `cited_via`, `domain`, `is_youtube`, `pub_date`, `ref_id`, `snippet`, `title`, `type`, `url`, `url_variants`

## Sources

`cited_via`: **safe_url** = URL listed in a `type:cite` object; **ref_id** = resolved from an `entities[].ref` such as `turn828649search4` back to this entry's `ref_id.ref_index`.

| cited | via | domain | ref | title | url |
|---|---|---|---|---|---|
| **YES** | safe_url,ref_id | byob.studio | search9 | Best Project Management Tools for Agencies: Asana vs… | https://byob.studio/blog/project-management-tools-agencies-asana-monday-clickup |
| **YES** | safe_url,ref_id | capterra.com | search2 | ClickUp Reviews 2026. Verified Reviews, Pros & Cons / Capter | https://www.capterra.com/p/158833/ClickUp/reviews/ |
| **YES** | safe_url,ref_id | clickup.com | search4 | 8 Best PM Tools for Agencies in 2026 (Tested) | https://clickup.com/learn/topic/project-management/industries/agencies/tools/ |
| **YES** | safe_url,ref_id | itsourcecode.com | search13 | Asana vs monday.com vs ClickUp 2026: Which for Your Team | https://itsourcecode.com/business-saas/asana-vs-monday-vs-clickup-2026-which-for-your-team/ |
| **YES** | safe_url,ref_id | stackfyi.com | search7 | Best Project Management Software for Agencies 2026 / StackFY | https://www.stackfyi.com/guides/best-pm-software-agencies-2026 |
| **YES** | safe_url,ref_id | toolradar.com | search8 | Best Project Management for Agencies (2026) / Toolradar | https://toolradar.com/guides/best-project-management-for-agencies |
| **YES** | safe_url | youtube.com | youtube5 | ClickUp vs Monday.com vs Asana - Which is Best? (2026) - You | https://www.youtube.com/watch?v=SzYhFDX_TV0 |
| no |  | agencypro.app | search10 | Best Project Management for Agencies (2026) / AgencyPro | https://agencypro.app/best/project-management-for-agencies |
| no |  | barakahsoft.com | search0 | Best Project Management Tools for Agencies 2026 - BarakahSof | https://www.barakahsoft.com/best-project-management-tools-for-agencies-2026/ |
| no |  | capterra.com | search1 | Teamwork.com Reviews 2026. Verified Reviews, Pros & Cons / C | https://www.capterra.com/p/120390/Teamwork-Projects/reviews/ |
| no |  | causivra.com | search16 | Asana vs ClickUp vs monday.com: Project Management for Small | https://www.causivra.com/insights/asana-vs-clickup-vs-monday |
| no |  | cloudwards.net | search0 | ClickUp Review 2026: Pros & Cons, Pricing, Features & Guides | https://www.cloudwards.net/clickup-review/ |
| no |  | dupple.com | search5 | Best Project Management Software for Small Business (2026) | https://dupple.com/learn/best-project-management-software-for-small-business |
| no |  | melororium.com | search1 | Best Project Management Software for Agencies 2026 / Meloror | https://melororium.com/blog/best-project-management-software-agencies-2026 |
| no |  | merchant-dash.com | search14 | monday.com vs ClickUp vs Asana (2026) / MerchantDash | https://merchant-dash.com/project-management/monday-com-vs-clickup-vs-asana |
| no |  | operdrive.com | search6 | Best Project Management Tools for Agencies 2026 — ClickUp vs | https://www.operdrive.com/research/best-project-management-tools-agencies-2026 |
| no |  | propicked.com | search15 | ClickUp vs Monday vs Asana 2026: Full Comparison / ProPicked | https://propicked.com/blog/clickup-vs-monday-vs-asana-2026 |
| no |  | reddit.com | reddit6 | For those interested, I'm migrating my team from Slack to Cl | https://www.reddit.com/r/clickup/comments/1u3w892/for_those_interested_im_migrating_my_team_from/ |
| no |  | reddit.com | reddit7 | Clickup is my world since years, but i am considering leavin | https://www.reddit.com/r/clickup/comments/1sez7gt/clickup_is_my_world_since_years_but_i_am/ |
| no |  | runflowagency.com | search12 | ClickUp vs Asana vs Monday.com for Agencies (2026) / Runflow | https://runflowagency.com/blog/clickup-vs-asana-vs-monday-for-agencies |
| no |  | sevensolvers.com | search11 | Best Project Management Software for Agencies and Developmen | https://www.sevensolvers.com/blog/best-project-management-software-for-agencies-and-development-teams-in-2026-top-9-compared |
| no |  | softoraguide.com | search2 | Best Project Management Tools for Agencies 2026 / Softora | https://softoraguide.com/blog/best-project-management-tools-for-agencies-2026/ |
| no |  | techstackdaily.com | search3 | Best Project Management Tools for Agencies 2026 | https://techstackdaily.com/listicle/best-project-management-tools-for-agencies-2026/ |
| no |  | trustradius.com | search3 | ClickUp Reviews: India Perspective / TrustRadius | https://www.trustradius.com/products/clickup/reviews/country/india?qs=bug-reports |
| no |  | youtube.com | youtube4 | Asana vs ClickUp vs Monday.com 2026: Which One Is Actually W | https://www.youtube.com/watch?v=NjOf3BrRV1k |
