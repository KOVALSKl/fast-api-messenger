def root_collection_item_exist(database, collection_name: str, item_id: str):
    item_ref = database.collection(collection_name).document(item_id)
    item_doc = item_ref.get()

    if item_doc.exists:
        return item_ref

    return None