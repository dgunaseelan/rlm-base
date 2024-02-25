public class RLM_AssetInfoUtility{
    @InvocableMethod(label = 'Calculate Asset Info'description = 'Returns Asset Renewal Info')
    public static void calculateAssetRenewInfo(List<CreateAssetOrderEvent> assetOrderCreationEvents){
        if (assetOrderCreationEvents.isEmpty()){
            return;
        }
        CreateAssetOrderEvent assetOrderCreationEvent = assetOrderCreationEvents.get(0);
        List<CreateAssetOrderDtlEvent> assetDetailEvents = assetOrderCreationEvent.AssetDetails;

        // Prepare a set to collect all OrderItemIds and AssetIds
        Set<Id> orderItemIds = new Set<Id>();
        Set<Id> assetIds = new Set<Id>();
        for (CreateAssetOrderDtlEvent event : assetDetailEvents){
            orderItemIds.add(event.OrderItemId);
            assetIds.add(event.AssetId);
        }

        // Fetch all related OrderItems outside the loop
        Map<Id, OrderItem> orderItemsMap = new Map<Id, OrderItem>([SELECT Id, ServiceDate, EndDate, OrderAction.Type, ProductSellingModel.SellingModelType, ProductSellingModel.PricingTermUnit, Product2.Name
                                                                   FROM OrderItem
                                                                   WHERE Id IN:orderItemIds]);

        // Fetch all related AssetContractRelationships outside the loop
        Map<Id, AssetContractRelationship> acrMap = new Map<Id, AssetContractRelationship>([SELECT Id, AssetId, Contract.ContractTerm
                                                                                            FROM AssetContractRelationship
                                                                                            WHERE AssetId IN:assetIds]);

        List<Asset> assetsToUpdate = new List<Asset>();

        for (CreateAssetOrderDtlEvent assetDetailEvent : assetDetailEvents){
            OrderItem oi = orderItemsMap.get(assetDetailEvent.OrderItemId);
            system.debug('Processing Order Item ' + oi.Id + ' for Product ' + oi.Product2.Name);

            Asset assetToUpdate = new Asset();
            assetToUpdate.Id = assetDetailEvent.AssetId;

            if (oi.OrderAction.Type == 'Add'){
                // Simplified logic for setting RenewalTerm and RenewalTermUnit based on conditions
                if (oi.ProductSellingModel.SellingModelType == 'TermDefined'){
                    Integer monthsBetween = oi.ServiceDate.monthsBetween(oi.EndDate);
                    if (oi.EndDate.day() > oi.ServiceDate.day()){
                        monthsBetween++;
                    }
                    assetToUpdate.RenewalTerm = Integer.valueOf(oi.ProductSellingModel.PricingTermUnit == 'Months' ? monthsBetween : monthsBetween / 12);
                    assetToUpdate.RenewalTermUnit = oi.ProductSellingModel.PricingTermUnit;
                } else if (oi.ProductSellingModel.SellingModelType == 'Evergreen'){
                    assetToUpdate.RenewalTerm = oi.ProductSellingModel.PricingTermUnit == 'Months' ? 12 : 1;
                    assetToUpdate.RenewalTermUnit = oi.ProductSellingModel.PricingTermUnit;
                } else{
                    assetToUpdate.RenewalTerm = 1;
                    assetToUpdate.RenewalTermUnit = 'Annual';
                }

                assetToUpdate.PricingSource = 'LastTransaction';
            } else{
                AssetContractRelationship acr = acrMap.get(assetDetailEvent.AssetId);
                if (acr != null){
                    assetToUpdate.RenewalTermUnit = 'Months';
                    assetToUpdate.RenewalTerm = acr.Contract.ContractTerm;
                    assetToUpdate.RenewalTerm = 12;
                    assetToUpdate.PricingSource = 'PriceBookListPrice';
                }
            }

            assetsToUpdate.add(assetToUpdate);
        }

        if (!assetsToUpdate.isEmpty()){
            upsert assetsToUpdate;
        }
    }

}