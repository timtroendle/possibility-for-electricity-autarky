import click
import pandas as pd
import geopandas as gpd
import pycountry


@click.command()
@click.argument("path_to_raw_cfs")
@click.argument("path_to_regions")
@click.argument("path_to_roof_classes")
@click.argument("path_to_output")
def pv_capacity_factors(path_to_raw_cfs, path_to_regions, path_to_roof_classes, path_to_output):
    """Derive PV capacity factors from renewable.ninja simulations on subnational level.

    Uses the roof classes to derive a single capacity factor for tilted roofs.
    """
    raw_cfs = pd.read_csv(path_to_raw_cfs, index_col=0)

    raw_cfs["tilt"] = raw_cfs.index.map(lambda x: int(x.split("_")[-1]))
    raw_cfs["orientation"] = raw_cfs.index.map(lambda x: x.split("_")[-2])
    raw_cfs["id"] = raw_cfs.index.map(lambda x: "_".join(x.split("_")[0:-2]))

    flat_pv_cfs = raw_cfs[raw_cfs["orientation"] == "flat"].set_index("id", drop=True)["pv"].rename(
        "flat_pv_capacity_factor"
    )
    raw_cfs = raw_cfs[raw_cfs["orientation"] != "flat"].copy()
    roof_stats = pd.read_csv(path_to_roof_classes)
    roof_stats_without_flat = roof_stats[roof_stats["orientation"] != "flat"].copy()
    roof_stats_without_flat.loc[:, "share of roof areas"] = (roof_stats_without_flat["share of roof areas"] /
                                                             roof_stats_without_flat["share of roof areas"].sum())
    assert roof_stats_without_flat["share of roof areas"].sum() == 1.0
    roof_stats_without_flat.loc[:, "tilt"] = roof_stats_without_flat["tilt"].map(round)

    raw_cfs = pd.merge(raw_cfs, roof_stats_without_flat, on=["orientation", "tilt"], how="left")
    assert (raw_cfs.groupby("id")["share of roof areas"].sum() == 1.0).all()

    raw_cfs["tilted_pv_capacity_factor"] = raw_cfs["share of roof areas"] * raw_cfs["pv"]
    tilted_pv_cfs = raw_cfs.groupby("id")["tilted_pv_capacity_factor"].sum()

    regions = gpd.read_file(path_to_regions).set_index("id")
    # fill nulls which stem from incompatible or missing regions (not necessary when
    # regions of simulated data match real regions)
    tilted_pv_cfs_country_avg = tilted_pv_cfs.groupby(
        [pycountry.countries.lookup(country[:3]).alpha_3 for country in tilted_pv_cfs.index]
    ).mean()
    flat_pv_cfs_country_avg = flat_pv_cfs.groupby(
        [pycountry.countries.lookup(country[:3]).alpha_3 for country in flat_pv_cfs.index]
    ).mean()
    tilted_pv_cfs = tilted_pv_cfs.reindex(regions.index)
    flat_pv_cfs = flat_pv_cfs.reindex(regions.index)
    print("PV capacity factors missing in these regions: {}. Replacing with national average.".format(
        list(tilted_pv_cfs[tilted_pv_cfs.isnull()].index))
    )
    tilted_pv_cfs[tilted_pv_cfs.isnull()] = regions.country_code[tilted_pv_cfs.isnull()].map(
        lambda country_code: tilted_pv_cfs_country_avg[country_code]
    )
    flat_pv_cfs[flat_pv_cfs.isnull()] = regions.country_code[flat_pv_cfs.isnull()].map(
        lambda country_code: flat_pv_cfs_country_avg[country_code]
    )
    regions["tilted_pv_capacity_factor"] = tilted_pv_cfs
    regions["flat_pv_capacity_factor"] = flat_pv_cfs
    assert ~regions.tilted_pv_capacity_factor.isnull().any()
    assert ~regions.flat_pv_capacity_factor.isnull().any()

    regions.loc[:, ["tilted_pv_capacity_factor", "flat_pv_capacity_factor", "geometry"]].to_file(
        path_to_output,
        driver="GeoJSON"
    )


if __name__ == "__main__":
    pv_capacity_factors()
