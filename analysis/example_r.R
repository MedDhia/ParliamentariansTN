#!/usr/bin/env Rscript
# Worked example: committee co-membership networks in igraph.
#
# Builds the projection from the bipartite incidence file rather than reading the
# pre-made edge list, because every projection embeds a weighting decision and
# you should own yours. Reports missingness before any statistic.
#
#   Rscript analysis/example_r.R
#
# Requires: igraph (install.packages("igraph")). Base R otherwise.

suppressPackageStartupMessages(library(igraph))

root      <- normalizePath(file.path(dirname(sys.frame(1)$ofile %||% "."), ".."), mustWork = FALSE)
`%||%`    <- function(a, b) if (is.null(a)) b else a
networks  <- file.path("data", "networks")
processed <- file.path("data", "processed")

read_tbl <- function(path) {
  read.csv(path, stringsAsFactors = FALSE, encoding = "UTF-8", na.strings = "")
}

incidence <- read_tbl(file.path(networks, "bipartite_person_committee.csv"))
nodes     <- read_tbl(file.path(networks, "nodes.csv"))
bloc_inc  <- read_tbl(file.path(networks, "bipartite_person_bloc.csv"))
mandates  <- read_tbl(file.path(processed, "mandates.csv"))

cat("ParliamentariansTN — committee co-membership networks\n")
cat(strrep("=", 68), "\n\n")

# ---------------------------------------------------------------------------
# Missingness first. Never report a statistic before saying what is missing.
# ---------------------------------------------------------------------------
cat("Missingness across all", nrow(nodes), "persons:\n")
for (v in c("gender", "birth_year", "governorate_id", "birth_governorate_id",
            "occupation_raw")) {
  n <- sum(!is.na(nodes[[v]]) & nodes[[v]] != "")
  cat(sprintf("  %-24s %4d / %d  (%.0f%%)\n", v, n, nrow(nodes),
              100 * n / nrow(nodes)))
}
cat("\n  governorate_id is the CONSTITUENCY's governorate (where the member was\n")
cat("  elected); birth_governorate_id is where they are from. Different variables.\n\n")

# ---------------------------------------------------------------------------
# One chamber at a time. Edges never cross chambers.
# ---------------------------------------------------------------------------
build_graph <- function(assembly) {
  inc <- incidence[incidence$assembly_id == assembly, ]
  if (nrow(inc) == 0) return(NULL)

  # bipartite graph, then project onto persons
  b <- graph_from_data_frame(
    data.frame(from = inc$person_id, to = inc$committee_id, stringsAsFactors = FALSE),
    directed = FALSE
  )
  V(b)$type <- V(b)$name %in% inc$committee_id
  proj <- bipartite_projection(b, which = "false")

  # attach attributes
  idx <- match(V(proj)$name, nodes$person_id)
  V(proj)$name_lat <- nodes$name_lat[idx]
  V(proj)$gender   <- nodes$gender[idx]
  V(proj)$region   <- nodes$region[idx]

  bl <- bloc_inc[bloc_inc$assembly_id == assembly, ]
  V(proj)$bloc <- bl$bloc_name_ar[match(V(proj)$name, bl$person_id)]
  proj
}

# Categorical assortativity, dropping vertices with a missing value and saying
# how many were dropped.
assort <- function(g, attr) {
  vals <- vertex_attr(g, attr)
  keep <- !is.na(vals) & vals != ""
  if (sum(keep) < 3) return(list(r = NA_real_, n = sum(keep)))
  sub <- induced_subgraph(g, V(g)[keep])
  f   <- as.factor(vertex_attr(sub, attr))
  list(r = assortativity_nominal(sub, as.integer(f), directed = FALSE),
       n = gorder(sub))
}

chambers <- sort(unique(incidence$assembly_id))
for (a in chambers) {
  g <- build_graph(a)
  if (is.null(g)) next
  cat(a, "\n")
  cat(strrep("-", 68), "\n")
  cat(sprintf("  nodes %d   edges %d   density %.3f   mean degree %.1f\n",
              gorder(g), gsize(g), edge_density(g), mean(degree(g))))
  cat(sprintf("  components %d   transitivity %.3f\n",
              components(g)$no, transitivity(g, type = "global")))

  for (v in c("bloc", "region", "gender")) {
    res <- assort(g, v)
    if (is.na(res$r)) {
      cat(sprintf("  assortativity by %-7s n/a (too few vertices with the attribute)\n", v))
    } else {
      cat(sprintf("  assortativity by %-7s r = %+.3f  (on %d vertices)\n",
                  v, res$r, res$n))
    }
  }

  d   <- degree(g)
  top <- head(order(d, decreasing = TRUE), 3)
  cat("  highest degree:\n")
  for (i in top) {
    cat(sprintf("    %-30s %3d  %s\n",
                V(g)$name_lat[i] %||% V(g)$name[i], d[i],
                ifelse(is.na(V(g)$bloc[i]), "", V(g)$bloc[i])))
  }
  cat("\n")
}

# ---------------------------------------------------------------------------
# Weighted projection: use Newman-corrected weights from the shipped edge list
# when tie strength matters. A 53-member bloc otherwise dominates everything.
# ---------------------------------------------------------------------------
edges <- read_tbl(file.path(networks, "edges_committee_comembership.csv"))
cat("Weighted committee network, weight vs weight_newman\n")
cat(strrep("-", 68), "\n")
for (a in chambers) {
  e <- edges[edges$assembly_id == a, ]
  if (nrow(e) == 0) next
  g <- graph_from_data_frame(e[, c("source", "target")], directed = FALSE)
  E(g)$weight <- e$weight
  s_naive <- strength(g)
  E(g)$weight <- e$weight_newman
  s_newman <- strength(g)
  rho <- suppressWarnings(cor(s_naive, s_newman, method = "spearman"))
  cat(sprintf("  %-10s Spearman(naive, Newman) = %+.3f  %s\n", a, rho,
              ifelse(!is.na(rho) && rho < 0.95,
                     "<- rankings differ; report which you used", "")))
}
cat("\nSee docs/NETWORK_GUIDE.md and docs/COVERAGE.md before drawing conclusions:\n")
cat("only ANC-1956, NCA-2011, ARP-2019 and ARP-2023 have person-level data,\n")
cat("and ARP-2014 is missing entirely, so there is no continuous 2011-2023 panel.\n")
