<?xml version='1.0' encoding='UTF-8'?>
<esdl:EnergySystem xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:esdl="http://www.tno.nl/esdl" id="e4e87ec0-2c1c-4569-afc8-752bbddadbcc" name="New Energy System" description="" esdlVersion="v2210" version="14">
  <instance xsi:type="esdl:Instance" id="618bbae6-25a7-46d0-bd7d-c1eb70cb2d31" name="Untitled instance">
    <area xsi:type="esdl:Area" id="GM0716" scope="MUNICIPALITY" name="Tholen">
      <asset xsi:type="esdl:PVInstallation" id="1907945a-5ffe-4c08-b9ce-9bc8689f943c" name="PVInstallation_1907" surfaceArea="7979" state="OPTIONAL">
        <costInformation xsi:type="esdl:CostInformation" id="c1ec6af9-b62b-40db-acdc-a84a7d2692ee">
          <investmentCosts xsi:type="esdl:SingleValue" value="871.0" id="2731c2a1-f70b-4db8-9f70-f531121d3745">
            <profileQuantityAndUnit xsi:type="esdl:QuantityAndUnitType" id="ed551dad-660a-4f65-84c6-3e108241a178" perUnit="WATT" description="Cost in EUR/kW" perMultiplier="KILO" physicalQuantity="COST" unit="EURO"/>
          </investmentCosts>
        </costInformation>
        <constraint xsi:type="esdl:RangedConstraint" id="d045e8d3-7f7b-40c5-a756-8c6534d6be2b" name="NewRangedConstraint" attributeReference="power">
          <range xsi:type="esdl:Range" maxValue="40000.0" name="PV installed capacity range" id="642eb1f7-22c8-4131-bf90-ff6e387a4a68" minValue="20000.0">
            <profileQuantityAndUnit xsi:type="esdl:QuantityAndUnitType" physicalQuantity="POWER" unit="WATT" description="Power in Watt" id="2b8f2157-4f95-4b2d-8944-cedc43a2cad9"/>
          </range>
        </constraint>
        <geometry xsi:type="esdl:Polygon" CRS="WGS84">
          <exterior xsi:type="esdl:SubPolygon">
            <point xsi:type="esdl:Point" lat="51.541484198065596" lon="4.227204322814942"/>
            <point xsi:type="esdl:Point" lat="51.541857872008826" lon="4.228159189224244"/>
            <point xsi:type="esdl:Point" lat="51.54112386671437" lon="4.228985309600831"/>
            <point xsi:type="esdl:Point" lat="51.54072349520013" lon="4.22801971435547"/>
          </exterior>
        </geometry>
        <port xsi:type="esdl:OutPort" carrier="279b10f4-c971-454d-9390-60a6970ab471" connectedTo="ad335aa5-2ebc-4148-85ac-b4276f64b7fc" name="Out" id="4c3f787e-df4f-4ab8-93ab-93dcde9827e2">
          <profile xsi:type="esdl:InfluxDBProfile" multiplier="28813.720" endDate="2020-01-01T00:00:00.000000+0100" measurement="standard_profiles" filters="" startDate="2019-01-01T00:00:00.000000+0100" field="Zon_deBilt" database="energy_profiles" port="8086" host="http://influxdb" id="6fc38691-9d02-4f58-bfde-455eb641cb82">
            <profileQuantityAndUnit xsi:type="esdl:QuantityAndUnitType" id="9d70cc41-750c-4c77-9f80-4bd89bc9020b" description="Energy in kWh" physicalQuantity="ENERGY" unit="WATTHOUR" multiplier="KILO"/>
          </profile>
        </port>
      </asset>
      <asset xsi:type="esdl:ElectricityDemand" id="2f528ef6-186e-4937-9967-d277f78e858a" name="ElectricityDemand_2f52">
        <geometry xsi:type="esdl:Point" CRS="WGS84" lat="51.54339257209525" lon="4.229489564895631"/>
        <port xsi:type="esdl:InPort" carrier="279b10f4-c971-454d-9390-60a6970ab471" connectedTo="bdb51e39-6cbf-48b1-84ab-bc342c4449f0" name="In" id="54c99cc4-fbc2-4d94-bc78-994eedb2cded">
          <profile xsi:type="esdl:InfluxDBProfile" measurement="standard_profiles" endDate="2019-12-31T22:00:00.000000+0000" multiplier="100.0" filters="" startDate="2018-12-31T23:00:00.000000+0000" field="E3C" database="energy_profiles" host="http://influxdb" port="8086" id="0de8679f-b0c1-4b17-830e-25955007bb2c">
			<profileQuantityAndUnit xsi:type="esdl:QuantityAndUnitType" id="5cd6a897-1ee4-4963-ac07-e4d917c65ab7" description="Energy in GJ" physicalQuantity="ENERGY" unit="JOULE" multiplier="GIGA"/>
          </profile>
        </port>
      </asset>
      <asset xsi:type="esdl:ElectricityNetwork" id="80e36970-0f1d-41f4-b371-f380ee3da8d3" name="ElectricityNetwork_80e3">
        <geometry xsi:type="esdl:Point" CRS="WGS84" lat="51.539896049575276" lon="4.229875802993775"/>
        <port xsi:type="esdl:InPort" carrier="279b10f4-c971-454d-9390-60a6970ab471" connectedTo="4c3f787e-df4f-4ab8-93ab-93dcde9827e2 9f17b954-d511-42cc-a51e-ccf7b6fb2bea" name="In" id="ad335aa5-2ebc-4148-85ac-b4276f64b7fc"/>
        <port xsi:type="esdl:OutPort" carrier="279b10f4-c971-454d-9390-60a6970ab471" connectedTo="54c99cc4-fbc2-4d94-bc78-994eedb2cded 19f8133c-51e5-4406-99eb-5489138255d0" name="Out" id="bdb51e39-6cbf-48b1-84ab-bc342c4449f0"/>
      </asset>
      <asset xsi:type="esdl:Import" id="bf483dd9-1f4e-4af1-9b23-ebf5eeae16d3" power="100000.0" name="Import_bf48">
        <costInformation xsi:type="esdl:CostInformation"/>
        <geometry xsi:type="esdl:Point" CRS="WGS84" lat="51.5383211921442" lon="4.227418899536134"/>
        <port xsi:type="esdl:OutPort" carrier="279b10f4-c971-454d-9390-60a6970ab471" connectedTo="ad335aa5-2ebc-4148-85ac-b4276f64b7fc" name="Out" id="9f17b954-d511-42cc-a51e-ccf7b6fb2bea"/>
      </asset>
      <asset xsi:type="esdl:Export" id="ef9b714e-ba35-4efb-9fbd-ff614af32c67" power="100000.0" name="Export_ef9b">
        <costInformation xsi:type="esdl:CostInformation">
          <marginalCosts xsi:type="esdl:SingleValue" name="Export_ef9b-MarginalCosts" id="55738e39-2d19-4c33-820c-334de748b2bd" value="0.1"/>
        </costInformation>
        <geometry xsi:type="esdl:Point" CRS="WGS84" lat="51.537907449373336" lon="4.228609800338746"/>
        <port xsi:type="esdl:InPort" carrier="279b10f4-c971-454d-9390-60a6970ab471" connectedTo="bdb51e39-6cbf-48b1-84ab-bc342c4449f0" name="In" id="19f8133c-51e5-4406-99eb-5489138255d0"/>
        <KPIs xsi:type="esdl:KPIs" id="4df9f3f1-eb33-4d75-873a-92cac70cd44a">
          <kpi xsi:type="esdl:DoubleKPI" name="Teacos_yearly_delimiting_percentage" id="df63c192-29b0-4e44-9348-ffe3d3eb0d17"/>
        </KPIs>
      </asset>
    </area>
  </instance>
  <energySystemInformation xsi:type="esdl:EnergySystemInformation" id="bc6a175b-6e55-44b4-a664-d0fda633920a">
    <quantityAndUnits xsi:type="esdl:QuantityAndUnits" id="543ca49f-c1bf-4f20-95e6-3dd6e2bc2e28">
      <quantityAndUnit xsi:type="esdl:QuantityAndUnitType" id="eb07bccb-203f-407e-af98-e687656a221d" perUnit="WATT" description="Energy in kWh per kW" perMultiplier="KILO" physicalQuantity="ENERGY" unit="WATTHOUR" multiplier="KILO"/>
      <quantityAndUnit xsi:type="esdl:QuantityAndUnitType" id="1a81a2e7-6ad4-472a-b8e5-973f82f454e9" description="Energy in GJ" physicalQuantity="ENERGY" unit="JOULE" multiplier="GIGA"/>
    </quantityAndUnits>
    <carriers xsi:type="esdl:Carriers" id="c505ce51-a17b-4fda-9ebf-dcdd73b2e900">
      <carrier xsi:type="esdl:ElectricityCommodity" id="279b10f4-c971-454d-9390-60a6970ab471" name="Electricity">
        <cost xsi:type="esdl:SingleValue" value="0.9" id="31ef506d-e259-4b48-a8c2-9a926586a32a"/>
      </carrier>
    </carriers>
  </energySystemInformation>
</esdl:EnergySystem>
