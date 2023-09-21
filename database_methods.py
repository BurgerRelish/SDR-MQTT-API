from typing import Dict, List, Optional
import supabase
import asyncio
from models import ControlUnitMQTTInfo



async def get_control_unit_info_async(client: supabase.Client, unit_id: str) -> ControlUnitMQTTInfo:
    # Initialize lists to store ingress and egress topics
    ingress_topics = []
    egress_topics = []

    # Query the topic_allocations table to find topics associated with the given unit_id
    topic_allocations_query = client.from_("topic_allocations").select("ingress", "egress", "topic_id", "unit_id").eq("unit_id", unit_id)
    topic_allocations_response = await topic_allocations_query.execute()

    if topic_allocations_response.error:
        raise Exception(f"Error querying topic_allocations: {topic_allocations_response.error}")

    # Iterate through the results and separate topics into ingress and egress
    for row in topic_allocations_response.data:
        if row["ingress"]:
            ingress_topics.append(row["topic_id"])
        else:
            egress_topics.append(row["topic_id"])

    # Initialize variables to store broker_address and port
    broker_address = None
    port = None

    # Query the brokers table to get the broker information for the topics
    if ingress_topics or egress_topics:
        brokers_query = client.from_("brokers").select("address", "port").in_("id", ingress_topics + egress_topics)
        brokers_response = await brokers_query.execute()

        if brokers_response.error:
            raise Exception(f"Error querying brokers: {brokers_response.error}")

        # Since the same broker information applies to all topics, use the first result
        if brokers_response.data:
            broker_address = brokers_response.data[0]["address"]
            port = str(brokers_response.data[0]["port"])

    # Create a ControlUnitMQTTInfo model to hold the results
    control_unit_info = ControlUnitMQTTInfo(
        ingress_topics=ingress_topics,
        egress_topics=egress_topics,
        broker_address=broker_address,
        port=port
    )

    return control_unit_info

# Example usage:
# async def main():
#     supabase_client = supabase.Client("YOUR_SUPABASE_URL", "YOUR_SUPABASE_API_KEY")
#     unit_id = "your_unit_id"
#     unit_info = await get_control_unit_info_async(supabase_client, unit_id)
#     print(unit_info)
#
# if __name__ == "__main__":
#     asyncio.run(main())