# Documentation

The submission keeps current operating contracts and the sources needed to understand and maintain the product. Start here instead of reading every document.

## Product and implementation

| Document | Use it for |
| :--- | :--- |
| [Repository overview](../README.md) | Product tour, local setup, architecture, configuration, checks. |
| [2.0 Blueprint](SIM-TAMY_2.0_AI_Updated_Blueprint_v2.1.md) | Current scope, task IDs, AI contracts, acceptance criteria. |
| [Platform contracts](v2/contracts.md) | Content, API, simulation, and web integration contracts. |
| [Demo accounts](v2/demo-login.md) | Fixed login, account separation, profile routing. |
| [Design system](../design-system/sim-tamy/MASTER.md) | Visual tokens and page conventions. |
| [OpenAPI](openapi.yaml) | Endpoint/response contract and input to generated web API types. |
| [API design](API_DESIGN.md) | API conventions and legacy session/instructor behavior. |
| [Deployment runbook](RUNBOOK-deploy.md) | Vercel/Render configuration, smoke checks, rollback. |
| [Architecture decisions](adr/) | Recorded decisions, including hosting and the 2.0 platform. |
| [Safety test matrix](security/safety-test-matrix.md) | Safety and AI-validation coverage map. |
| [PRD](PRD.md) | Original requirements, engine/session contracts, backlog. |
| [Family simulations](FAMILY_SIMULATIONS.md) | Legacy family-mode implementation and retention notes. |

The Blueprint takes precedence for 2.0 scope, followed by ADRs and the PRD where the Blueprint is silent. Historical plans in retained specifications describe their original milestone; current behavior is recorded in the contracts and repository overview. The retired example player redirects `/replay` to `/lab`; report consequence timelines and engine replay remain supported.

## Content and provenance

| Resource | Use it for |
| :--- | :--- |
| [Knowledge base](<knowledge base/>) | Research PDF, textbook catalogue PDF, catalogue JSON. |
| [Thai midwifery content](v2/thai-midwifery-content.md) | Current implementation and provenance notes. |
| [Content authoring guide](content-authoring-guide.md) | Schema editing, source locators, validation. |
| [Curriculum source synthesis](SIM-TAMY-curriculum-and-solution.md) | Background synthesis still cited by source research. |
| [Source research](research/) | Provenance documents referenced by authored scenarios and source audits. |
| [Published content](../content/) | Runtime YAML and the application's source registry. |

Research files keep their paths so scenario source locators remain valid. Textbook catalogue records are metadata, not full-text licenses or proof of professional review.

## Local working material

Historical UI review screenshots, dated experiment/load reports, old feature proposals, demo scripts, and the superseded 1.x concept document are no longer tracked. Their paths are listed in [.gitignore](../.gitignore); previous committed versions remain available through Git history. Existing local copies are preserved during submission cleanup.

New documentation should have one clear owner and purpose. Update the existing contract or guide when possible; keep temporary notes and test output under `.tmp/`.
