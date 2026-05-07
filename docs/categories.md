# Server categories

Reference list of subject categories per preprint server. Used to choose
sensible defaults for the `CATEGORIES` action input.

Status legend:

- **canonical** — full list, verified
- **sampled** — partial; needs full pagination from a longer-lived runner
- **unreachable** — blocked from CI sandbox; re-run elsewhere

## bioRxiv (canonical, 25)

Source: `https://api.biorxiv.org/details/biorxiv/{date1}/{date2}/{cursor}/json`

```text
animal behavior and cognition
biochemistry
bioengineering
bioinformatics
biophysics
cancer biology
cell biology
developmental biology
ecology
evolutionary biology
genetics
genomics
immunology
microbiology
molecular biology
neuroscience
paleontology
pathology
pharmacology and toxicology
physiology
plant biology
scientific communication and education
synthetic biology
systems biology
zoology
```

## medRxiv (sampled, 29 observed; ~35–45 expected)

Source: `https://api.biorxiv.org/details/medrxiv/{date1}/{date2}/{cursor}/json`

Pagination timed out from the enumeration sandbox after the first few pages.
This list is the union of one 1-week window and one partial 1-year window.
Re-run from a CI runner with longer timeouts to converge.

```text
addiction medicine
allergy and immunology
cardiovascular medicine
dentistry and oral medicine
dermatology
endocrinology
epidemiology
forensic medicine
genetic and genomic medicine
geriatric medicine
health economics
health informatics
health policy
health systems and quality improvement
infectious diseases
intensive care and critical care medicine
medical education
nephrology
neurology
nutrition
obstetrics and gynecology
occupational and environmental health
oncology
ophthalmology
pain medicine
pathology
pediatrics
pharmacology and therapeutics
psychiatry and clinical psychology
public and global health
radiology and imaging
rehabilitation medicine and physical therapy
respiratory medicine
sexual and reproductive health
sports medicine
surgery
```

## psyArXiv (canonical, 6 top-level; 234 total OSF taxonomy nodes)

Source: `https://api.osf.io/v2/preprint_providers/psyarxiv/taxonomies/`

Top-level (recommended for `CATEGORIES` filter — the full 234-node taxonomy
is too granular for a coarse filter):

```text
Engineering Psychology
Life Sciences
Meta-science
Neuroscience
Psychiatry
Social and Behavioral Sciences
```

The 228 depth-1 children include `Cognitive Neuroscience`, `Clinical
Psychology`, `Behavioral Economics`, `Computational Modeling`, and similar.
Fetch the full list via the source URL above when implementing.

## chemRxiv (unreachable, pending)

Source: `https://chemrxiv.org/engage/chemrxiv/public-api/v1/items` (categories
embedded in item records)

The chemRxiv public API is fronted by Cloudflare and returns a challenge page
to non-browser clients from the enumeration sandbox. Approaches that work:

- run the fetch from a real browser DevTools session (paste cookies into a
  `curl` invocation)
- run from a CI runner where Cloudflare flags a verified UA
- use the official client library if/when one ships

Tracked in [issue #69](https://github.com/qte77/gha-biorxiv-stats-action/issues/69).
