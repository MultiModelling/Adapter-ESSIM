import esdl
from influxdb import InfluxDBClient
from pyecore.ecore import EDate

from tno.essim_adapter.model.essim import ESSIM

if __name__ == "__main__":
    # <asset xsi:type="esdl:HeatingDemand" id="6992d3af-f3b7-4c91-8d81-67d861df8726" name="HeatingDemand_6992">
    #   <geometry xsi:type="esdl:Point" CRS="WGS84" lat="53.45044250555688" lon="5.753059387207032"/>
    #   <port xsi:type="esdl:InPort" id="2d09f9f3-3567-470f-a229-c654f41cadce" connectedTo="ffa0d830-11de-45c6-8f54-685ae2aec22a 16c06616-b849-4624-8ab4-121657bb1c66" carrier="7c6439be-42df-4f09-8263-a3f1e49ee0ce" name="In">
    #     <profile xsi:type="esdl:InfluxDBProfile" database="energy_profiles" startDate="2015-01-01T00:00:00.000000+0100" host="http://geis.hesi.energy" field="G1A" filters="" multiplier="50.0" endDate="2016-01-01T00:00:00.000000+0100" id="78eba100-6031-4c08-bad1-de4de1c4a086" port="8086" measurement="nedu_aardgas_2015-2018">
    #       <profileQuantityAndUnit xsi:type="esdl:QuantityAndUnitType" id="eb07bccb-203f-407e-af98-e687656a221d" description="Energy in GJ" multiplier="GIGA" unit="JOULE" physicalQuantity="ENERGY"/>
    #     </profile>
    #   </port>
    # </asset>

    profile = esdl.InfluxDBProfile(
        id="78eba100-6031-4c08-bad1-de4de1c4a086",
        host="http://geis.hesi.energy",
        port=8086,
        database="energy_profiles",
        measurement="nedu_aardgas_2015-2018",
        field="G1A",
        startDate=EDate.from_string("2016-01-01T00:00:00.000000+0100"),
        endDate=EDate.from_string("2017-01-01T00:00:00.000000+0100"),
        multiplier=50.0
    )

    profile.profileQuantityAndUnit = esdl.QuantityAndUnitType(
        id="123",
        physicalQuantity=esdl.PhysicalQuantityEnum.COST,
        unit=esdl.UnitEnum.EURO,
        perMultiplier=esdl.MultiplierEnum.MEGA,
        perUnit=esdl.UnitEnum.WATTHOUR,
        description="COST in EUR/MWh"
    )

    mdl = ESSIM()

    profile_info = mdl.query_esdl_influxdb_profile(profile)
    print(profile_info)

    profile_info.influxdb_info.database = "test"
    mdl.save_profile_to_influxdb(profile_info)
