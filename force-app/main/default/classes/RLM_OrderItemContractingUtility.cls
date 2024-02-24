public class RLM_OrderItemContractingUtility {
    
    @InvocableMethod (label='Calculate Contract Info' description='Returns an Contract End Date based on last Order Item')
    public static List<OrderInfoResults> calculateOrderInfoForContract(List<Id> inputOrderIds){
        Id oId = inputOrderIds.get(0);

        Order o = [SELECT Id, EffectiveDate FROM Order WHERE Id =: oId].get(0);
       

        List<OrderInfoResults> results = new List<OrderInfoResults>();

        OrderInfoResults result = new OrderInfoResults();

        List<OrderItem> subOrderItems = [SELECT Id, ProductSellingModel.SellingModelType
                                            FROM OrderItem 
                                            WHERE (ProductSellingModel.SellingModelType != 'One Time' AND OrderId =: oId)];

        result.subscriptionItemCount = subOrderItems.size();

        if(subOrderItems.size() > 0){
            List<OrderItem> sortedOrderItems = [SELECT Id, ServiceDate, EndDate 
                                            FROM OrderItem 
                                            WHERE (EndDate != null AND OrderId =: oId) 
                                            ORDER BY EndDate DESC];

            if(sortedOrderItems.size() > 0){
                result.outEndDate = sortedOrderItems.get(0).EndDate;
                result.outContractTerm = o.EffectiveDate.monthsBetween(sortedOrderItems.get(0).EndDate);
                if (sortedOrderItems.get(0).EndDate.day() > o.EffectiveDate.day()) result.outContractTerm++;
            }
        }else {
            result.outEndDate = null;
            result.outContractTerm = 1;
        }

        result.addOrderActionCount = [SELECT Id, OrderId, Type FROM OrderAction WHERE (Type = 'Add' AND OrderId =: oId)].size();
        
        result.amendOrderActionCount = [SELECT Id, OrderId, Type FROM OrderAction WHERE (Type = 'Amend' AND OrderId =: oId)].size();

        result.renewOrderActionCount = [SELECT Id, OrderId, Type FROM OrderAction WHERE (Type = 'Renew' AND OrderId =: oId)].size();

        results.add(result);
        
        return results;

    }

    public class OrderInfoResults{
        @InvocableVariable 
        public Date outEndDate;

        @InvocableVariable 
        public Integer outContractTerm;

        @InvocableVariable
        public Integer subscriptionItemCount;

        @InvocableVariable 
        public Integer addOrderActionCount;

        @InvocableVariable 
        public Integer amendOrderActionCount;

        @InvocableVariable 
        public Integer renewOrderActionCount;
    }
}