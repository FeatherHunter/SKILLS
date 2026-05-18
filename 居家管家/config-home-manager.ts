// config-home-manager.ts
// Home Manager Skill - SkillBoard Configuration
// DB: home.db (tables: items / item_locations / item_tags / accounts)

export const HomeManagerConfig = {

  // ── 1. meta ──────────────────────────────────────────────────────────────
  meta: {
    name: "home-manager",
    label: "Home Manager",
    icon: "House",
    description: "Household item + account/password management. Supports item entry, search, inventory, outfit recommendation, and account management.",
    dbFiles: ["home.db"],
  },

  // ── 2. schema ────────────────────────────────────────────────────────────
  schema: {
    tables: [
      // ── items (main item table) ──────────────────────────────────────
      {
        name: "items",
        fields: [
          { name: "id", type: "INTEGER", label: "ID", primaryKey: true },
          { name: "name", type: "TEXT", label: "Name", nullable: false },
          { name: "category", type: "TEXT", label: "Category", nullable: false },
          { name: "owner", type: "TEXT", label: "Owner", default: "使用者" },
          { name: "purchase_price", type: "REAL", label: "Unit Price", unit: "元", format: "currency" },
          { name: "remark", type: "TEXT", label: "Remark" },
          { name: "photo", type: "TEXT", label: "Photo Path" },
          { name: "access_count", type: "INTEGER", label: "Access Count", format: "number" },
          { name: "last_accessed_at", type: "TEXT", label: "Last Accessed", format: "datetime" },
          { name: "created_at", type: "TEXT", label: "Created At", format: "datetime" },
          { name: "updated_at", type: "TEXT", label: "Updated At", format: "datetime" },
        ],
      },
      // ── item_locations (per-location storage records) ─────────────────
      {
        name: "item_locations",
        fields: [
          { name: "id", type: "INTEGER", label: "Location ID", primaryKey: true },
          { name: "item_id", type: "INTEGER", label: "Item ID", nullable: false },
          { name: "location", type: "TEXT", label: "Location Path", nullable: false },
          { name: "quantity", type: "INTEGER", label: "Quantity", default: 1, format: "number" },
          { name: "reason", type: "TEXT", label: "Reason" },
          {
            name: "location_status",
            type: "TEXT",
            label: "Location Status",
            options: ["在家", "备用", "穿着中", "旅游中", "洗护中", "借用中", "维修中", "已用完", "快递中", "待处理", "已废弃"],
          },
          { name: "purchase_date", type: "TEXT", label: "Purchase Date", format: "date" },
          { name: "expiration_date", type: "TEXT", label: "Expiration Date", format: "date" },
          { name: "created_at", type: "TEXT", label: "Created At", format: "datetime" },
          { name: "updated_at", type: "TEXT", label: "Updated At", format: "datetime" },
        ],
      },
      // ── item_tags (item tags) ──────────────────────────────────────────
      {
        name: "item_tags",
        fields: [
          { name: "id", type: "INTEGER", label: "ID", primaryKey: true },
          { name: "item_id", type: "INTEGER", label: "Item ID", nullable: false },
          { name: "tag", type: "TEXT", label: "Tag", nullable: false },
        ],
      },
      // ── accounts (encrypted account storage) ────────────────────────
      {
        name: "accounts",
        fields: [
          { name: "id", type: "INTEGER", label: "ID", primaryKey: true },
          { name: "platform", type: "TEXT", label: "Platform", nullable: false },
          { name: "username", type: "TEXT", label: "Username" },
          { name: "encrypted_password", type: "TEXT", label: "Password (Encrypted)" },
          { name: "tags", type: "TEXT", label: "Tags" },
          { name: "note", type: "TEXT", label: "Note" },
          { name: "created_at", type: "TEXT", label: "Created At", format: "datetime" },
          { name: "updated_at", type: "TEXT", label: "Updated At", format: "datetime" },
        ],
      },
    ],
  },

  // ── 3. queries ────────────────────────────────────────────────────────────
  queries: [
    // ── 3.1 Item search (name/tag/location fuzzy search) ─────────────────
    {
      id: "item-search",
      label: "Item Search",
      sql: `SELECT DISTINCT i.id, i.name, i.category, i.owner, i.purchase_price,
                   i.remark, i.photo, i.access_count, i.last_accessed_at,
                   il.location, il.quantity, il.location_status,
                   il.purchase_date, il.expiration_date,
                   GROUP_CONCAT(t.tag) as tags
            FROM items i
            LEFT JOIN item_locations il ON i.id = il.item_id
            LEFT JOIN item_tags t ON i.id = t.item_id
            WHERE (? = '' OR i.name LIKE '%' || ? || '%')
              AND (? = '' OR i.category = ?)
              AND (? = '' OR il.location LIKE '%' || ? || '%')
              AND (? = '' OR t.tag = ?)
              AND (? = '' OR il.location_status = ?)
            GROUP BY i.id
            ORDER BY i.access_count DESC
            LIMIT ?`,
      params: [
        { name: "name", type: "text", label: "Item Name" },
        { name: "name", type: "text", label: "Item Name" },
        { name: "category", type: "text", label: "Category" },
        { name: "category", type: "text", label: "Category" },
        { name: "location", type: "text", label: "Location" },
        { name: "location", type: "text", label: "Location" },
        { name: "tag", type: "text", label: "Tag" },
        { name: "tag", type: "text", label: "Tag" },
        { name: "status", type: "text", label: "Status" },
        { name: "status", type: "text", label: "Status" },
        { name: "limit", type: "text", label: "Result Limit", default: "20" },
      ],
    },

    // ── 3.2 Item list (filter by location/status/category, sortable) ────
    {
      id: "item-list",
      label: "Item List",
      sql: `SELECT i.id, i.name, i.category, i.owner, i.purchase_price,
                   i.remark, i.photo, i.access_count, i.last_accessed_at,
                   il.location, il.quantity, il.location_status,
                   il.purchase_date, il.expiration_date,
                   GROUP_CONCAT(t.tag) as tags
            FROM items i
            LEFT JOIN item_locations il ON i.id = il.item_id
            LEFT JOIN item_tags t ON i.id = t.item_id
            WHERE (? = '' OR il.location LIKE '%' || ? || '%')
              AND (? = '' OR il.location_status = ?)
              AND (? = '' OR i.category = ?)
              AND (? = '' OR i.owner = ?)
            GROUP BY i.id
            ORDER BY
              CASE WHEN ? = 'recent' THEN i.last_accessed_at END DESC,
              CASE WHEN ? = 'frequent' THEN i.access_count END DESC,
              CASE WHEN ? = 'updated' THEN i.updated_at END DESC,
              CASE WHEN ? = 'dormant' THEN i.last_accessed_at END ASC,
              CASE WHEN ? = 'name' OR ? = '' THEN i.name END ASC
            LIMIT ?`,
      params: [
        { name: "location", type: "text", label: "Location" },
        { name: "location", type: "text", label: "Location" },
        { name: "status", type: "text", label: "Status" },
        { name: "status", type: "text", label: "Status" },
        { name: "category", type: "text", label: "Category" },
        { name: "category", type: "text", label: "Category" },
        { name: "owner", type: "text", label: "Owner" },
        { name: "owner", type: "text", label: "Owner" },
        { name: "sort", type: "text", label: "Sort By" },
        { name: "sort", type: "text", label: "Sort By" },
        { name: "sort", type: "text", label: "Sort By" },
        { name: "sort", type: "text", label: "Sort By" },
        { name: "sort", type: "text", label: "Sort By" },
        { name: "sort", type: "text", label: "Sort By" },
        { name: "limit", type: "text", label: "Result Limit", default: "100" },
      ],
    },

    // ── 3.3 Item detail (single item for detail view) ───────────────────
    {
      id: "item-detail",
      label: "Item Detail",
      sql: `SELECT i.*, il.location, il.quantity, il.reason, il.location_status,
                   il.purchase_date, il.expiration_date,
                   GROUP_CONCAT(t.tag) as tags
            FROM items i
            LEFT JOIN item_locations il ON i.id = il.item_id
            LEFT JOIN item_tags t ON i.id = t.item_id
            WHERE i.id = ?
            GROUP BY il.id
            ORDER BY il.id`,
      params: [
        { name: "id", type: "text", label: "Item ID" },
      ],
    },

    // ── 3.4 Inventory (all items at a specific location) ─────────────────
    {
      id: "inventory",
      label: "Inventory",
      sql: `SELECT DISTINCT i.id, i.name, i.category, i.owner,
                   il.location as matched_location,
                   il.quantity as matched_quantity,
                   il.location_status,
                   il.purchase_date, il.expiration_date,
                   GROUP_CONCAT(t.tag) as tags
            FROM items i
            JOIN item_locations il ON i.id = il.item_id
            LEFT JOIN item_tags t ON i.id = t.item_id
            WHERE il.location LIKE '%' || ? || '%'
            GROUP BY i.id, il.id
            ORDER BY i.category, i.name`,
      params: [
        { name: "location", type: "text", label: "Inventory Location" },
      ],
    },

    // ── 3.5 Frequent items (by access count) ─────────────────────────────
    {
      id: "stats-frequent",
      label: "Frequent Items",
      sql: `SELECT i.*, GROUP_CONCAT(t.tag) as tags
            FROM items i
            LEFT JOIN item_tags t ON i.id = t.item_id
            GROUP BY i.id
            ORDER BY i.access_count DESC
            LIMIT ?`,
      params: [
        { name: "limit", type: "text", label: "Result Limit", default: "20" },
      ],
    },

    // ── 3.6 Dormant items (long time no access, by last_accessed_at asc) ─
    {
      id: "stats-dormant",
      label: "Long Unused Items",
      sql: `SELECT i.*, GROUP_CONCAT(t.tag) as tags
            FROM items i
            LEFT JOIN item_tags t ON i.id = t.item_id
            WHERE i.last_accessed_at IS NOT NULL
            GROUP BY i.id
            ORDER BY i.last_accessed_at ASC
            LIMIT ?`,
      params: [
        { name: "limit", type: "text", label: "Result Limit", default: "20" },
      ],
    },

    // ── 3.7 Summary statistics (total + status distribution + category) ──
    {
      id: "stats-summary",
      label: "Summary Statistics",
      sql: `SELECT
              (SELECT COUNT(*) FROM items) as total_items,
              (SELECT COUNT(DISTINCT item_id) FROM item_locations) as total_locations`,
      params: [],
    },

    // ── 3.8 Tag list ───────────────────────────────────────────────────
    {
      id: "tag-list",
      label: "Tag List",
      sql: `SELECT tag, COUNT(*) as cnt
            FROM item_tags
            GROUP BY tag
            ORDER BY cnt DESC`,
      params: [],
    },

    // ── 3.9 Account list (password hidden) ─────────────────────────────
    {
      id: "account-list",
      label: "Account List",
      sql: `SELECT id, platform, username, tags, note, created_at, updated_at
            FROM accounts
            ORDER BY platform`,
      params: [],
    },

    // ── 3.10 Express/in-transit items ─────────────────────────────────
    {
      id: "express-items",
      label: "In-Transit Items",
      sql: `SELECT i.id, i.name, i.category,
                   il.location, il.quantity, il.location_status,
                   il.purchase_date, il.expiration_date,
                   GROUP_CONCAT(t.tag) as tags
            FROM items i
            JOIN item_locations il ON i.id = il.item_id
            LEFT JOIN item_tags t ON i.id = t.item_id
            WHERE il.location_status = '快递中'
            GROUP BY i.id, il.id
            ORDER BY i.name`,
      params: [],
    },

    // ── 3.11 Status distribution for charts ───────────────────────────
    {
      id: "status-summary",
      label: "Status Distribution",
      sql: `SELECT il.location_status, COUNT(DISTINCT i.id) as cnt
            FROM items i
            JOIN item_locations il ON i.id = il.item_id
            GROUP BY il.location_status
            ORDER BY cnt DESC`,
      params: [],
      chartType: "doughnut",
    },

    // ── 3.12 Category distribution for charts ────────────────────────
    {
      id: "category-summary",
      label: "Category Distribution",
      sql: `SELECT category as location_status, COUNT(*) as cnt
            FROM items
            GROUP BY category
            ORDER BY cnt DESC`,
      params: [],
      chartType: "bar",
    },
  ],

  // ── 4. actions ────────────────────────────────────────────────────────────
  actions: [
    // ── 4.1 Add new item ───────────────────────────────────────────────
    {
      id: "add-item",
      label: "Add Item",
      type: "insert",
      targetTable: "items",
      fields: [
        { field: "name", required: true, source: "user-input", prompt: "Item name" },
        { field: "category", required: true, source: "user-input", prompt: "Category (e.g. 衣物/食品/数码)" },
        { field: "owner", source: "user-input", prompt: "Owner (default: 使用者)", default: "使用者" },
        { field: "purchase_price", source: "user-input", prompt: "Unit price (元)", format: "currency" },
        { field: "remark", source: "user-input", prompt: "Remark" },
        { field: "photo", source: "user-input", prompt: "Photo path" },
      ],
    },

    // ── 4.2 Add location record (item + location) ──────────────────────
    {
      id: "add-location",
      label: "Add Location",
      type: "insert",
      targetTable: "item_locations",
      fields: [
        { field: "item_id", required: true, source: "user-input", prompt: "Item ID" },
        { field: "location", required: true, source: "user-input", prompt: "Location path (e.g. 客厅/冰箱/上层, min 2 levels)" },
        { field: "quantity", required: true, source: "user-input", prompt: "Quantity", default: "1", format: "number" },
        { field: "location_status", source: "user-input", prompt: "Status", options: ["在家", "备用", "穿着中", "旅游中", "洗护中", "借用中", "维修中", "已用完", "快递中", "待处理", "已废弃"] },
        { field: "purchase_date", source: "user-input", prompt: "Purchase date (YYYY-MM-DD)", format: "date" },
        { field: "expiration_date", source: "user-input", prompt: "Expiration date (YYYY-MM-DD)", format: "date" },
        { field: "reason", source: "user-input", prompt: "Reason (optional)" },
      ],
    },

    // ── 4.3 Update item basic info ─────────────────────────────────────
    {
      id: "update-item",
      label: "Update Item",
      type: "update",
      targetTable: "items",
      fields: [
        { field: "id", required: true, source: "user-input", prompt: "Item ID" },
        { field: "name", source: "user-input", prompt: "Item name" },
        { field: "category", source: "user-input", prompt: "Category" },
        { field: "owner", source: "user-input", prompt: "Owner" },
        { field: "purchase_price", source: "user-input", prompt: "Unit price", format: "currency" },
        { field: "remark", source: "user-input", prompt: "Remark" },
        { field: "photo", source: "user-input", prompt: "Photo path" },
      ],
    },

    // ── 4.4 Update location status ────────────────────────────────────
    {
      id: "update-location-status",
      label: "Update Location Status",
      type: "update",
      targetTable: "item_locations",
      fields: [
        { field: "id", required: true, source: "user-input", prompt: "Location ID" },
        { field: "location_status", required: true, source: "user-input", prompt: "New status", options: ["在家", "备用", "穿着中", "旅游中", "洗护中", "借用中", "维修中", "已用完", "快递中", "待处理", "已废弃"] },
      ],
    },

    // ── 4.5 Quantity change (set directly) ─────────────────────────────
    {
      id: "update-quantity",
      label: "Adjust Quantity",
      type: "update",
      targetTable: "item_locations",
      fields: [
        { field: "id", required: true, source: "user-input", prompt: "Location ID" },
        { field: "quantity", required: true, source: "user-input", prompt: "New quantity (set directly)", format: "number" },
      ],
    },

    // ── 4.6 Move item to new location ──────────────────────────────────
    {
      id: "update-location-move",
      label: "Move Item",
      type: "update",
      targetTable: "item_locations",
      fields: [
        { field: "id", required: true, source: "user-input", prompt: "Location ID" },
        { field: "location", required: true, source: "user-input", prompt: "New location (path)" },
      ],
    },

    // ── 4.7 Update location dates ──────────────────────────────────────
    {
      id: "update-location-dates",
      label: "Update Location Dates",
      type: "update",
      targetTable: "item_locations",
      fields: [
        { field: "id", required: true, source: "user-input", prompt: "Location ID" },
        { field: "purchase_date", source: "user-input", prompt: "Purchase date (YYYY-MM-DD)", format: "date" },
        { field: "expiration_date", source: "user-input", prompt: "Expiration date (YYYY-MM-DD)", format: "date" },
      ],
    },

    // ── 4.8 Set item tags ───────────────────────────────────────────────
    {
      id: "set-item-tags",
      label: "Set Tags",
      type: "update",
      targetTable: "item_tags",
      fields: [
        { field: "item_id", required: true, source: "user-input", prompt: "Item ID" },
        { field: "tag", required: true, source: "user-input", prompt: "Tags (comma-separated)" },
      ],
    },

    // ── 4.9 Add account (encrypted) ─────────────────────────────────────
    {
      id: "add-account",
      label: "Add Account",
      type: "insert",
      targetTable: "accounts",
      fields: [
        { field: "platform", required: true, source: "user-input", prompt: "Platform name" },
        { field: "username", source: "user-input", prompt: "Username / Account" },
        { field: "encrypted_password", required: true, source: "user-input", prompt: "Password" },
        { field: "tags", source: "user-input", prompt: "Tags (e.g. 社交,工作)" },
        { field: "note", source: "user-input", prompt: "Note" },
      ],
    },

    // ── 4.10 Delete account ────────────────────────────────────────────
    {
      id: "del-account",
      label: "Delete Account",
      type: "delete",
      targetTable: "accounts",
      fields: [
        { field: "id", required: true, source: "user-input", prompt: "Account ID" },
      ],
    },
  ],

  // ── 5. views ─────────────────────────────────────────────────────────────
  views: [
    // ── 5.1 Item search ─────────────────────────────────────────────────
    {
      id: "search",
      label: "Search",
      icon: "MagnifyingGlass",
      components: {
        table: { queryId: "item-search", columns: ["name", "category", "location", "quantity", "location_status", "tags"], sortable: true, pageSize: 20 },
      },
    },

    // ── 5.2 Item list (filter + sort) ──────────────────────────────────
    {
      id: "list",
      label: "All Items",
      icon: "List",
      components: {
        table: { queryId: "item-list", columns: ["name", "category", "location", "quantity", "location_status", "purchase_price", "tags"], sortable: true, pageSize: 50 },
      },
    },

    // ── 5.3 Item detail ────────────────────────────────────────────────
    {
      id: "detail",
      label: "Item Detail",
      icon: "Info",
      components: {
        table: { queryId: "item-detail" },
      },
    },

    // ── 5.4 Inventory ──────────────────────────────────────────────────
    {
      id: "inventory",
      label: "Inventory",
      icon: "ClipboardText",
      components: {
        table: { queryId: "inventory", columns: ["name", "category", "matched_location", "matched_quantity", "location_status", "purchase_date", "expiration_date", "tags"], sortable: true },
      },
    },

    // ── 5.5 Frequent items ─────────────────────────────────────────────
    {
      id: "stats-frequent",
      label: "Frequent Items",
      icon: "TrendUp",
      components: {
        table: { queryId: "stats-frequent", columns: ["name", "category", "access_count", "last_accessed_at", "tags"], sortable: true },
      },
    },

    // ── 5.6 Long unused ────────────────────────────────────────────────
    {
      id: "stats-dormant",
      label: "Long Unused",
      icon: "TrendDown",
      components: {
        table: { queryId: "stats-dormant", columns: ["name", "category", "access_count", "last_accessed_at", "tags"], sortable: true },
      },
    },

    // ── 5.7 Summary stats ──────────────────────────────────────────────
    {
      id: "stats-summary",
      label: "Statistics",
      icon: "ChartBar",
      components: {
        chart: { queryId: "status-summary" },
      },
    },

    // ── 5.8 Tag management ─────────────────────────────────────────────
    {
      id: "tags",
      label: "Tags",
      icon: "Tag",
      components: {
        table: { queryId: "tag-list", columns: ["tag", "cnt"] },
      },
    },

    // ── 5.9 Account management ────────────────────────────────────────
    {
      id: "accounts",
      label: "Accounts",
      icon: "Key",
      components: {
        table: { queryId: "account-list", columns: ["platform", "username", "tags", "note", "created_at"], sortable: true },
      },
    },

    // ── 5.10 Add item form ─────────────────────────────────────────────
    {
      id: "add",
      label: "Add Item",
      icon: "Plus",
      components: {
        form: { actionId: "add-item" },
      },
    },

    // ── 5.11 Express/in-transit items ──────────────────────────────────
    {
      id: "express",
      label: "In Transit",
      icon: "Package",
      components: {
        table: { queryId: "express-items", columns: ["name", "category", "location", "quantity", "location_status", "tags"], sortable: true },
      },
    },
  ],
}